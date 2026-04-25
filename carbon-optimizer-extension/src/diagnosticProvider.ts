import * as vscode from 'vscode';
import { Bridge } from './bridge';

export interface Issue {
  issue_id: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  line_number: number;
  description: string;
  suggested_fix: string;
  carbon_impact_score: string;
}

export interface AnalysisResult {
  functions: unknown[];
  issues: Issue[];
  parse_time_ms: number;
}

export function mapSeverity(severity: string): vscode.DiagnosticSeverity {
  switch (severity) {
    case 'HIGH':   return vscode.DiagnosticSeverity.Error;
    case 'MEDIUM': return vscode.DiagnosticSeverity.Warning;
    case 'LOW':    return vscode.DiagnosticSeverity.Information;
    default:       return vscode.DiagnosticSeverity.Information;
  }
}

export class DiagnosticProvider {
  private collection: vscode.DiagnosticCollection;
  private statusBarItem: vscode.StatusBarItem;
  private outputChannel: vscode.OutputChannel;
  // Store issues per URI for hover provider access
  private issueMap = new Map<string, Issue[]>();

  constructor(private readonly bridge: Bridge, outputChannel?: vscode.OutputChannel) {
    this.collection = vscode.languages.createDiagnosticCollection('carbon-optimizer');
    this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    this.outputChannel = outputChannel ?? vscode.window.createOutputChannel('Carbon Optimizer');
  }

  register(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument((doc) => {
        if (doc.languageId === 'python') {
          this.onSave(doc);
        }
      }),
      vscode.workspace.onDidCloseTextDocument((doc) => {
        this.onClose(doc);
      }),
      this.collection,
      this.statusBarItem,
    );
  }

  private async onSave(document: vscode.TextDocument): Promise<void> {
    this.statusBarItem.text = '$(sync~spin) Carbon: Analyzing…';
    this.statusBarItem.show();

    try {
      const result = await this.bridge.call<AnalysisResult>('analyze_efficiency', {
        code: document.getText(),
      });

      const diagnostics = this.toDiagnostics(result.issues, document);
      this.collection.set(document.uri, diagnostics);
      this.issueMap.set(document.uri.toString(), result.issues);

      const count = result.issues.length;
      this.statusBarItem.text = count === 0
        ? '$(check) Carbon: No issues'
        : `$(warning) Carbon: ${count} issue${count === 1 ? '' : 's'}`;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.outputChannel.appendLine(`[Carbon Optimizer] Analysis error: ${message}`);
      this.collection.delete(document.uri);
      this.issueMap.delete(document.uri.toString());
      this.statusBarItem.text = '$(error) Carbon: Error';
    }
  }

  private onClose(document: vscode.TextDocument): void {
    this.collection.delete(document.uri);
    this.issueMap.delete(document.uri.toString());
  }

  toDiagnostics(issues: Issue[], document: vscode.TextDocument): vscode.Diagnostic[] {
    return issues.map((issue) => {
      const lineIndex = Math.max(0, issue.line_number - 1);
      const lineText = document.lineAt(lineIndex).text;
      const range = new vscode.Range(
        new vscode.Position(lineIndex, 0),
        new vscode.Position(lineIndex, lineText.length),
      );
      const diagnostic = new vscode.Diagnostic(range, issue.description, mapSeverity(issue.severity));
      diagnostic.source = 'Carbon Optimizer';
      diagnostic.code = issue.suggested_fix;
      return diagnostic;
    });
  }

  getIssuesForUri(uri: vscode.Uri): Issue[] {
    return this.issueMap.get(uri.toString()) ?? [];
  }

  dispose(): void {
    this.collection.dispose();
    this.statusBarItem.dispose();
  }
}
