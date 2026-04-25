import * as vscode from 'vscode';
import { Bridge } from './bridge';
import { ReportPanel } from './reportPanel';

interface ConfigIssue {
  issue_id: string;
  file_path: string;
  line_number: number;
  description: string;
  carbon_impact_score: string;
  remediation: string;
  example_fix: string;
}

export class ConfigScanner {
  /** Set of workspace folder URI strings already scanned this session. */
  private hasScanned = new Set<string>();
  private outputChannel: vscode.OutputChannel;

  constructor(
    private readonly bridge: Bridge,
    private readonly reportPanel: ReportPanel,
    outputChannel?: vscode.OutputChannel,
  ) {
    this.outputChannel = outputChannel ?? vscode.window.createOutputChannel('Carbon Optimizer');
  }

  /**
   * Register workspace folder listeners and scan any already-open folders.
   * Called once on extension activation.
   */
  register(context: vscode.ExtensionContext): void {
    // Scan folders that are already open when the extension activates
    const folders = vscode.workspace.workspaceFolders ?? [];
    for (const folder of folders) {
      this.scan(folder.uri.fsPath, folder.uri.toString());
    }

    // Scan newly added workspace folders
    context.subscriptions.push(
      vscode.workspace.onDidChangeWorkspaceFolders((event) => {
        for (const folder of event.added) {
          this.scan(folder.uri.fsPath, folder.uri.toString());
        }
      }),
    );
  }

  /**
   * Run the config scan for a workspace root path.
   * Skips if this folder has already been scanned this session.
   * Runs asynchronously so workspace startup is not delayed.
   */
  private scan(workspaceRoot: string, folderKey: string): void {
    if (this.hasScanned.has(folderKey)) {
      return;
    }
    this.hasScanned.add(folderKey);

    // Run asynchronously — do not await
    this._doScan(workspaceRoot).catch((err) => {
      const message = err instanceof Error ? err.message : String(err);
      this.outputChannel.appendLine(`[Carbon Optimizer] Config scan error: ${message}`);
    });
  }

  private async _doScan(workspaceRoot: string): Promise<void> {
    try {
      const issues = await this.bridge.call<ConfigIssue[]>('analyze_configs', {
        workspace_root: workspaceRoot,
      });

      if (!Array.isArray(issues) || issues.length === 0) {
        return;
      }

      const count = issues.length;
      const message = `Carbon Optimizer: ${count} deployment config issue${count === 1 ? '' : 's'} found. Click to view.`;

      const action = await vscode.window.showInformationMessage(message, 'View Issues');
      if (action === 'View Issues') {
        this.reportPanel.renderConfigIssues(issues);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.outputChannel.appendLine(`[Carbon Optimizer] Config scan failed: ${message}`);
      // Do not show a notification — log only
    }
  }

  dispose(): void {
    // Nothing to clean up — subscriptions are managed by context.subscriptions
  }
}
