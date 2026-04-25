import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { Bridge } from './bridge';

interface Metrics {
  execution_time_ms: number;
  memory_used_bytes: number;
  energy_kwh: number;
  co2_grams: number;
}

interface Comparison {
  execution_time_improvement_pct: number;
  memory_improvement_pct: number;
  co2_improvement_pct: number;
  summary: string;
}

interface Report {
  analysis: { functions: unknown[]; issues: unknown[]; parse_time_ms: number };
  original_metrics: Metrics;
  optimized_code: string;
  optimized_metrics: Metrics;
  comparison: Comparison;
}

interface ConfigIssue {
  issue_id: string;
  file_path: string;
  line_number: number;
  description: string;
  carbon_impact_score: string;
  remediation: string;
  example_fix: string;
}

export class ReportPanel {
  private panel: vscode.WebviewPanel | undefined;
  private lastHtml = '';
  private _webviewReady = false;
  private _pendingContent: string | undefined;

  constructor(
    private readonly bridge: Bridge,
    private readonly extensionPath: string,
  ) {}

  show(): void {
    if (this.panel) {
      this.panel.reveal();
      this._updateContent();
    } else {
      this._webviewReady = false;
      this._pendingContent = undefined;

      this.panel = vscode.window.createWebviewPanel(
        'carbonOptimizerReport',
        'Carbon Optimizer Report',
        vscode.ViewColumn.Beside,
        { enableScripts: true },
      );

      const htmlPath = path.join(this.extensionPath, 'media', 'report.html');
      let html: string;
      try {
        html = fs.readFileSync(htmlPath, 'utf8');
      } catch {
        html = this._fallbackHtml();
      }
      this.panel.webview.html = html;

      this.panel.webview.onDidReceiveMessage((message) => {
        if (message.command === 'ready') {
          this._webviewReady = true;
          if (this._pendingContent !== undefined) {
            this.panel?.webview.postMessage({ command: 'setContent', html: this._pendingContent });
            this._pendingContent = undefined;
          } else {
            this._updateContent();
          }
        } else if (message.command === 'optimize') {
          this._runOptimize();
        }
      });

      this.panel.onDidDispose(() => {
        this.panel = undefined;
        this._webviewReady = false;
        this._pendingContent = undefined;
      });
    }
  }

  private _getActivePythonDocument(): vscode.TextDocument | undefined {
    const active = vscode.window.activeTextEditor;
    if (active?.document.languageId === 'python') {
      return active.document;
    }
    // Webview panels steal focus, so also check all visible editors
    return vscode.window.visibleTextEditors.find(
      (e) => e.document.languageId === 'python',
    )?.document;
  }

  private _updateContent(): void {
    const doc = this._getActivePythonDocument();
    if (!doc) {
      this._setContent(this._noFileHtml());
    } else {
      this._setContent(this._optimizeButtonHtml());
    }
  }

  private async _runOptimize(): Promise<void> {
    const document = this._getActivePythonDocument();
    if (!document) {
      this._setContent(this._noFileHtml());
      return;
    }

    this._setContent('<p class="loading">⏳ Running optimization pipeline…</p>');

    try {
      const report = await this.bridge.call<Report>('run_pipeline', {
        code: document.getText(),
      });
      this._setContent(this.renderReport(report));
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this._setContent(this.renderError(message));
    }
  }

  renderReport(report: Report): string {
    const { original_metrics: orig, optimized_metrics: opt, comparison: comp, optimized_code } = report;

    const pct = (val: number) => {
      const cls = val >= 0 ? 'improvement-positive' : 'improvement-negative';
      const sign = val >= 0 ? '▼' : '▲';
      return `<span class="${cls}">${sign} ${Math.abs(val).toFixed(2)}%</span>`;
    };

    const metricsTable = (m: Metrics) => `
      <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Execution time</td><td>${m.execution_time_ms.toFixed(2)} ms</td></tr>
        <tr><td>Memory used</td><td>${(m.memory_used_bytes / 1024).toFixed(1)} KB</td></tr>
        <tr><td>Energy</td><td>${m.energy_kwh.toExponential(4)} kWh</td></tr>
        <tr><td>CO₂</td><td>${m.co2_grams.toExponential(4)} g</td></tr>
      </table>`;

    return `
      <button id="optimize-btn">🔄 Re-optimize</button>
      <h3>📊 Original Metrics</h3>
      ${metricsTable(orig)}
      <h3>✨ Optimized Code</h3>
      <div class="code-block">${this._escapeHtml(optimized_code)}</div>
      <h3>📊 Optimized Metrics</h3>
      ${metricsTable(opt)}
      <h3>📈 Comparison</h3>
      <table>
        <tr><th>Metric</th><th>Improvement</th></tr>
        <tr><td>Execution time</td><td>${pct(comp.execution_time_improvement_pct)}</td></tr>
        <tr><td>Memory</td><td>${pct(comp.memory_improvement_pct)}</td></tr>
        <tr><td>CO₂</td><td>${pct(comp.co2_improvement_pct)}</td></tr>
      </table>
      <div class="summary">💬 ${this._escapeHtml(comp.summary)}</div>
    `;
  }

  renderConfigIssues(issues: ConfigIssue[]): void {
    if (issues.length === 0) {
      this._setContent('<p>✅ No deployment config issues found.</p>');
      return;
    }

    const badgeClass = (score: string) => {
      switch (score) {
        case 'HIGH': return 'badge-high';
        case 'MEDIUM': return 'badge-medium';
        default: return 'badge-low';
      }
    };

    const html = `
      <h3>⚙️ Deployment Config Issues (${issues.length})</h3>
      ${issues.map((issue) => `
        <div class="config-issue">
          <strong class="${badgeClass(issue.carbon_impact_score)}">[${issue.carbon_impact_score}]</strong>
          <strong>${this._escapeHtml(issue.issue_id)}</strong>
          — ${this._escapeHtml(issue.file_path)}:${issue.line_number}<br/>
          <em>${this._escapeHtml(issue.description)}</em><br/>
          <strong>Fix:</strong> ${this._escapeHtml(issue.remediation)}<br/>
          <div class="code-block">${this._escapeHtml(issue.example_fix)}</div>
        </div>
      `).join('')}
    `;

    this.show();
    this._setContent(html);
  }

  renderError(message: string): string {
    return `<div class="error-message">❌ <strong>Error:</strong> ${this._escapeHtml(message)}</div>
            <button id="optimize-btn">🔄 Try Again</button>`;
  }

  private _setContent(html: string): void {
    this.lastHtml = html;
    if (!this._webviewReady) {
      this._pendingContent = html;
      return;
    }
    this.panel?.webview.postMessage({ command: 'setContent', html });
  }

  private _noFileHtml(): string {
    return '<p>Open a Python file to run optimization.</p>';
  }

  private _optimizeButtonHtml(): string {
    return '<button id="optimize-btn">⚡ Optimize</button><p>Click to analyze and optimize the active Python file.</p>';
  }

  private _fallbackHtml(): string {
    return `<!DOCTYPE html><html><body>
      <h2>🌱 Carbon Optimizer</h2>
      <div id="content"></div>
      <script>
        const vscode = acquireVsCodeApi();
        vscode.postMessage({ command: 'ready' });
        document.addEventListener('click', e => {
          if (e.target && e.target.id === 'optimize-btn') vscode.postMessage({ command: 'optimize' });
        });
        window.addEventListener('message', e => {
          if (e.data.command === 'setContent') document.getElementById('content').innerHTML = e.data.html;
        });
      </script>
    </body></html>`;
  }

  private _escapeHtml(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  dispose(): void {
    this.panel?.dispose();
  }
}
