"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReportPanel = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class ReportPanel {
    constructor(bridge, extensionPath) {
        this.bridge = bridge;
        this.extensionPath = extensionPath;
        this.lastHtml = '';
    }
    show(activeDocument) {
        if (this.panel) {
            this.panel.reveal();
        }
        else {
            this.panel = vscode.window.createWebviewPanel('carbonOptimizerReport', 'Carbon Optimizer Report', vscode.ViewColumn.Beside, { enableScripts: true });
            // Load the HTML template
            const htmlPath = path.join(this.extensionPath, 'media', 'report.html');
            let html;
            try {
                html = fs.readFileSync(htmlPath, 'utf8');
            }
            catch {
                html = this._fallbackHtml();
            }
            this.panel.webview.html = html;
            // Handle messages from the WebView
            this.panel.webview.onDidReceiveMessage((message) => {
                if (message.command === 'optimize') {
                    this._runOptimize(activeDocument);
                }
            });
            this.panel.onDidDispose(() => {
                this.panel = undefined;
            });
        }
        if (!activeDocument || activeDocument.languageId !== 'python') {
            this._setContent(this._noFileHtml());
            return;
        }
        // Show optimize button
        this._setContent(this._optimizeButtonHtml());
    }
    async _runOptimize(document) {
        if (!document) {
            this._setContent(this._noFileHtml());
            return;
        }
        this._setContent('<p class="loading">⏳ Running optimization pipeline…</p>');
        try {
            const report = await this.bridge.call('run_pipeline', {
                code: document.getText(),
            });
            this._setContent(this.renderReport(report));
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this._setContent(this.renderError(message));
        }
    }
    renderReport(report) {
        const { original_metrics: orig, optimized_metrics: opt, comparison: comp, optimized_code } = report;
        const pct = (val) => {
            const cls = val >= 0 ? 'improvement-positive' : 'improvement-negative';
            const sign = val >= 0 ? '▼' : '▲';
            return `<span class="${cls}">${sign} ${Math.abs(val).toFixed(2)}%</span>`;
        };
        const metricsTable = (m) => `
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
    renderConfigIssues(issues) {
        if (issues.length === 0) {
            this._setContent('<p>✅ No deployment config issues found.</p>');
            return;
        }
        const badgeClass = (score) => {
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
    renderError(message) {
        return `<div class="error-message">❌ <strong>Error:</strong> ${this._escapeHtml(message)}</div>
            <button id="optimize-btn">🔄 Try Again</button>`;
    }
    _setContent(html) {
        this.lastHtml = html;
        this.panel?.webview.postMessage({ command: 'setContent', html });
    }
    _noFileHtml() {
        return '<p>Open a Python file to run optimization.</p>';
    }
    _optimizeButtonHtml() {
        return '<button id="optimize-btn">⚡ Optimize</button><p>Click to analyze and optimize the active Python file.</p>';
    }
    _fallbackHtml() {
        return `<!DOCTYPE html><html><body>
      <h2>🌱 Carbon Optimizer</h2>
      <div id="content"></div>
      <script>
        const vscode = acquireVsCodeApi();
        document.addEventListener('click', e => {
          if (e.target && e.target.id === 'optimize-btn') vscode.postMessage({ command: 'optimize' });
        });
        window.addEventListener('message', e => {
          if (e.data.command === 'setContent') document.getElementById('content').innerHTML = e.data.html;
        });
      </script>
    </body></html>`;
    }
    _escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
    dispose() {
        this.panel?.dispose();
    }
}
exports.ReportPanel = ReportPanel;
//# sourceMappingURL=reportPanel.js.map