import * as vscode from 'vscode';
import * as path from 'path';
import { Bridge } from './bridge';
import { DiagnosticProvider } from './diagnosticProvider';
import { StruggleTracker } from './struggleTracker';
import { ReportPanel } from './reportPanel';
import { ConfigScanner } from './configScanner';

let bridge: Bridge | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  // ── 1. Read configuration ────────────────────────────────────────────────
  const config = vscode.workspace.getConfiguration('carbonOptimizer');
  let pythonPath = config.get<string>('pythonPath') ?? 'python3';

  // Resolve the backend server script path relative to the extension
  const serverScriptPath = path.join(
    context.extensionPath, '..', 'kiro-carbon-optimizer', 'backend_server.py'
  );

  // ── 2. Instantiate components ────────────────────────────────────────────
  bridge = new Bridge(pythonPath, serverScriptPath);
  const diagnosticProvider = new DiagnosticProvider(bridge);
  const struggleTracker = new StruggleTracker();
  const reportPanel = new ReportPanel(bridge, context.extensionPath);
  const configScanner = new ConfigScanner(bridge, reportPanel);

  // ── 3. Start the backend ─────────────────────────────────────────────────
  try {
    await bridge.start();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(
      `Carbon Optimizer: Failed to start backend. Check that Python is installed at "${pythonPath}". Error: ${message}`
    );
  }

  // ── 4. Register components ───────────────────────────────────────────────
  diagnosticProvider.register(context);
  configScanner.register(context);

  // ── 5. Register command: carbonOptimizer.openReport ──────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('carbonOptimizer.openReport', () => {
      const activeDoc = vscode.window.activeTextEditor?.document;
      reportPanel.show(activeDoc);
    }),
  );

  // ── 6. Register HoverProvider for Python files ───────────────────────────
  context.subscriptions.push(
    vscode.languages.registerHoverProvider('python', {
      provideHover(document, position) {
        const issues = diagnosticProvider.getIssuesForUri(document.uri);
        const lineNumber = position.line + 1; // issues use 1-based line numbers
        const issue = issues.find((i) => i.line_number === lineNumber);
        if (!issue) return undefined;

        const md = new vscode.MarkdownString();
        md.appendMarkdown(`**Carbon Optimizer** — ${issue.description}\n\n`);
        md.appendMarkdown(`💡 **Suggested fix:** ${issue.suggested_fix}`);
        return new vscode.Hover(md);
      },
    }),
  );

  // ── 7. Struggle detection on save ────────────────────────────────────────
  const outputChannel = vscode.window.createOutputChannel('Carbon Optimizer');
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      if (document.languageId !== 'python') return;

      const filePath = document.uri.fsPath;
      const triggered = struggleTracker.recordSave(filePath);

      if (triggered) {
        const filename = path.basename(filePath);
        vscode.window.showWarningMessage(
          `Carbon Optimizer: You've saved ${filename} 5 times in 10 minutes. ` +
          `You may be in an AI retry loop. Consider adding more context.`
        );

        // Notify the backend struggle detector
        try {
          const lineCount = document.lineCount;
          const signals = await bridge!.call<Array<{ message?: string }>>('on_edit_generated', {
            file_path: filePath,
            line_range: [1, lineCount],
          });

          if (Array.isArray(signals)) {
            for (const signal of signals) {
              if (signal.message) {
                outputChannel.appendLine(`[Struggle] ${signal.message}`);
              }
            }
          }
        } catch {
          // Silently ignore backend errors for struggle detection
        }

        struggleTracker.reset(filePath);
      }
    }),
  );

  // ── 8. React to pythonPath configuration changes ─────────────────────────
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      if (event.affectsConfiguration('carbonOptimizer.pythonPath')) {
        const newConfig = vscode.workspace.getConfiguration('carbonOptimizer');
        const newPythonPath = newConfig.get<string>('pythonPath') ?? 'python3';

        bridge?.dispose();
        bridge = new Bridge(newPythonPath, serverScriptPath);
        try {
          await bridge.start();
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          vscode.window.showErrorMessage(
            `Carbon Optimizer: Failed to restart backend with new Python path "${newPythonPath}". Error: ${message}`
          );
        }
      }
    }),
  );
}

export function deactivate(): void {
  bridge?.dispose();
  bridge = undefined;
}
