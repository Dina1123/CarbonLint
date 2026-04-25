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
        this._webviewReady = false;
    }
    show() {
        if (this.panel) {
            this.panel.reveal();
            this._updateContent();
        }
        else {
            this._webviewReady = false;
            this._pendingContent = undefined;
            this.panel = vscode.window.createWebviewPanel('carbonOptimizerReport', 'Carbon Optimizer Report', vscode.ViewColumn.Beside, { enableScripts: true });
            const htmlPath = path.join(this.extensionPath, 'media', 'report.html');
            let html;
            try {
                html = fs.readFileSync(htmlPath, 'utf8');
            }
            catch {
                html = this._fallbackHtml();
            }
            this.panel.webview.html = html;
            this.panel.webview.onDidReceiveMessage((message) => {
                if (message.command === 'ready') {
                    this._webviewReady = true;
                    if (this._pendingContent !== undefined) {
                        this.panel?.webview.postMessage({ command: 'setContent', html: this._pendingContent });
                        this._pendingContent = undefined;
                    }
                    else {
                        this._updateContent();
                    }
                }
                else if (message.command === 'optimize') {
                    this._runOptimize();
                }
                else if (message.command === 'copy') {
                    void this._copyCode(message.code);
                }
                else if (message.command === 'apply') {
                    void this._applyCode(message.code);
                }
            });
            const editorWatcher = vscode.window.onDidChangeActiveTextEditor(() => {
                if (this._webviewReady) {
                    this._updateContent();
                }
            });
            this.panel.onDidDispose(() => {
                editorWatcher.dispose();
                this.panel = undefined;
                this._webviewReady = false;
                this._pendingContent = undefined;
            });
        }
    }
    _getActivePythonDocument() {
        const active = vscode.window.activeTextEditor;
        if (active?.document.languageId === 'python') {
            return active.document;
        }
        return vscode.window.visibleTextEditors.find((e) => e.document.languageId === 'python')?.document;
    }
    _updateContent() {
        const doc = this._getActivePythonDocument();
        if (!doc) {
            this._setContent(this._noFileHtml());
        }
        else {
            this._setContent(this._readyHtml(path.basename(doc.fileName)));
        }
    }
    async _runOptimize() {
        const document = this._getActivePythonDocument();
        if (!document) {
            this._setContent(this._noFileHtml());
            return;
        }
        const fileName = path.basename(document.fileName);
        this._setContent(this._loadingHtml(fileName));
        try {
            const report = await this.bridge.call('run_pipeline', {
                code: document.getText(),
            });
            this._setContent(this.renderReport(report, fileName));
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this._setContent(this._errorHtml(message, fileName));
        }
    }
    async _copyCode(code) {
        await vscode.env.clipboard.writeText(code);
        this.panel?.webview.postMessage({ command: 'copyResult' });
    }
    async _applyCode(code) {
        const document = this._getActivePythonDocument();
        if (!document) {
            vscode.window.showErrorMessage('Carbon Optimizer: No active Python file to apply changes to.');
            this.panel?.webview.postMessage({ command: 'applyResult', success: false });
            return;
        }
        try {
            const editor = await vscode.window.showTextDocument(document);
            const success = await editor.edit((editBuilder) => {
                const fullRange = new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length));
                editBuilder.replace(fullRange, code);
            });
            this.panel?.webview.postMessage({ command: 'applyResult', success });
            if (success) {
                vscode.window.showInformationMessage('Carbon Optimizer: Optimized code applied. Press Ctrl+Z to undo.');
            }
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            vscode.window.showErrorMessage(`Carbon Optimizer: Failed to apply code — ${msg}`);
            this.panel?.webview.postMessage({ command: 'applyResult', success: false });
        }
    }
    // ── Rendered HTML sections ─────────────────────────────────────────────────
    renderReport(report, fileName) {
        const { original_metrics: orig, optimized_metrics: opt, comparison: comp, optimized_code } = report;
        const f = this._escapeHtml(fileName);
        const pct = (val) => {
            const cls = val >= 0 ? 'improvement-positive' : 'improvement-negative';
            const arrow = val >= 0 ? '▼' : '▲';
            return `<span class="${cls}">${arrow} ${Math.abs(val).toFixed(1)}%</span>`;
        };
        const metricsTable = (m) => `
      <table>
        <thead><tr><th>Metric</th><th>Measured value</th><th>What that means</th></tr></thead>
        <tbody>
          <tr>
            <td>Run time</td>
            <td>${m.execution_time_ms.toFixed(2)} ms</td>
            <td class="muted">How long the code took to execute</td>
          </tr>
          <tr>
            <td>Memory used</td>
            <td>${(m.memory_used_bytes / 1024).toFixed(1)} KB</td>
            <td class="muted">Peak RAM consumed during execution</td>
          </tr>
          <tr class="highlight-row">
            <td>Energy used</td>
            <td><strong>${m.energy_kwh.toExponential(3)} kWh</strong></td>
            <td class="context">≈ ${this._humanizeEnergy(m.energy_kwh)}</td>
          </tr>
          <tr class="highlight-row">
            <td>Carbon emitted</td>
            <td><strong>${m.co2_grams.toExponential(3)} g CO₂</strong></td>
            <td class="context">≈ ${this._humanizeCO2(m.co2_grams)}</td>
          </tr>
        </tbody>
      </table>`;
        return `
      <div class="report-toolbar">
        <div class="file-pill">🐍 ${f}</div>
        <button id="optimize-btn" class="btn-secondary">🔄 Re-run Analysis</button>
      </div>

      <div class="report-intro">
        This report shows the estimated carbon footprint of <strong>${f}</strong> and
        what it would look like after automated optimization.
      </div>

      <section class="report-section">
        <div class="section-heading">
          <span class="section-icon">⚡</span>
          <div>
            <h3>Current Carbon Footprint</h3>
            <p class="section-desc">This is how much energy <strong>${f}</strong> consumes right now, every time it runs.</p>
          </div>
        </div>
        ${metricsTable(orig)}
      </section>

      <section class="report-section">
        <div class="section-heading">
          <span class="section-icon">✨</span>
          <div>
            <h3>Optimized Version of Your Code</h3>
            <p class="section-desc">Our optimizer rewrote <strong>${f}</strong> to use less CPU and memory.
            Review the changes below, then copy or apply directly to your file.</p>
          </div>
        </div>
        <div class="code-toolbar">
          <span class="code-label">Suggested rewrite</span>
          <div class="code-actions">
            <button id="copy-btn" class="action-btn" title="Copy to clipboard">⧉ Copy</button>
            <button id="apply-btn" class="action-btn" title="Replace file with this code">↙ Apply to File</button>
          </div>
        </div>
        <div class="code-block" id="optimized-code">${this._escapeHtml(optimized_code)}</div>
      </section>

      <section class="report-section">
        <div class="section-heading">
          <span class="section-icon">📊</span>
          <div>
            <h3>Optimized Carbon Footprint</h3>
            <p class="section-desc">What the energy cost looks like after applying the changes above.</p>
          </div>
        </div>
        ${metricsTable(opt)}
      </section>

      <section class="report-section savings-section">
        <div class="section-heading">
          <span class="section-icon">💚</span>
          <div>
            <h3>Your Savings — Every Time This Code Runs</h3>
            <p class="section-desc">Switching to the optimized version saves this much carbon on each execution.</p>
          </div>
        </div>
        <table>
          <thead><tr><th>What improves</th><th>By how much</th></tr></thead>
          <tbody>
            <tr><td>Run time</td><td>${pct(comp.execution_time_improvement_pct)}</td></tr>
            <tr><td>Memory used</td><td>${pct(comp.memory_improvement_pct)}</td></tr>
            <tr class="highlight-row"><td><strong>Carbon emitted</strong></td><td><strong>${pct(comp.co2_improvement_pct)}</strong></td></tr>
          </tbody>
        </table>
        <div class="summary-box">💬 ${this._escapeHtml(comp.summary)}</div>
      </section>
    `;
    }
    renderConfigIssues(issues) {
        if (issues.length === 0) {
            this._setContent('<p class="muted">✅ No deployment config issues found.</p>');
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
      <div class="report-intro">
        Found <strong>${issues.length} deployment configuration issue${issues.length === 1 ? '' : 's'}</strong>
        that could be wasting energy in your infrastructure.
      </div>
      ${issues.map((issue) => `
        <div class="config-issue">
          <div class="config-issue-header">
            <span class="badge ${badgeClass(issue.carbon_impact_score)}">${issue.carbon_impact_score} IMPACT</span>
            <strong>${this._escapeHtml(issue.issue_id)}</strong>
            <span class="muted">— ${this._escapeHtml(path.basename(issue.file_path))}${issue.line_number ? `:${issue.line_number}` : ''}</span>
          </div>
          <p>${this._escapeHtml(issue.description)}</p>
          <p><strong>How to fix:</strong> ${this._escapeHtml(issue.remediation)}</p>
          <div class="code-block">${this._escapeHtml(issue.example_fix)}</div>
        </div>
      `).join('')}
    `;
        this.show();
        this._setContent(html);
    }
    // ── State screens ──────────────────────────────────────────────────────────
    _noFileHtml() {
        return `
      <div class="state-screen">
        <div class="state-icon">🌱</div>
        <h3>No Python file open</h3>
        <p>Open a <strong>.py</strong> file in the editor and this panel will let you
        analyze its carbon footprint and get an optimized version.</p>
      </div>`;
    }
    _readyHtml(fileName) {
        return `
      <div class="file-pill" style="margin-bottom:16px">🐍 ${this._escapeHtml(fileName)}</div>
      <div class="state-screen">
        <div class="state-icon">⚡</div>
        <h3>Ready to analyze</h3>
        <p>Click the button below to measure the carbon footprint of
        <strong>${this._escapeHtml(fileName)}</strong> and generate an optimized version.</p>
        <button id="optimize-btn" style="margin-top:12px">⚡ Analyze &amp; Optimize</button>
        <div class="info-box">
          <strong>What happens:</strong>
          <ul>
            <li>We profile the energy cost of your current code</li>
            <li>We apply code transformations to reduce CPU cycles and memory</li>
            <li>We show a before / after carbon footprint comparison</li>
          </ul>
        </div>
      </div>`;
    }
    _loadingHtml(fileName) {
        return `
      <div class="file-pill" style="margin-bottom:16px">🐍 ${this._escapeHtml(fileName)}</div>
      <div class="state-screen">
        <div class="state-icon spin">⚙️</div>
        <h3>Analyzing ${this._escapeHtml(fileName)}…</h3>
        <p class="muted">Profiling energy usage and running optimization passes. This may take a few seconds.</p>
      </div>`;
    }
    _errorHtml(message, fileName) {
        return `
      <div class="file-pill" style="margin-bottom:16px">🐍 ${this._escapeHtml(fileName)}</div>
      <div class="error-message">
        <strong>❌ Analysis failed</strong><br>
        ${this._escapeHtml(message)}
      </div>
      <button id="optimize-btn">🔄 Try Again</button>`;
    }
    // ── Helpers ────────────────────────────────────────────────────────────────
    _humanizeEnergy(kwh) {
        const ledSeconds = kwh / 2.778e-6; // 10 W LED = 2.778e-6 kWh/s
        if (ledSeconds < 0.001)
            return `${(ledSeconds * 1e6).toFixed(1)} µs of a 10 W LED bulb`;
        if (ledSeconds < 1)
            return `${(ledSeconds * 1000).toFixed(1)} ms of a 10 W LED bulb`;
        if (ledSeconds < 60)
            return `${ledSeconds.toFixed(2)} s of a 10 W LED bulb`;
        return `${(ledSeconds / 60).toFixed(2)} min of a 10 W LED bulb`;
    }
    _humanizeCO2(grams) {
        const meters = grams / 0.12; // avg car ≈ 120 g CO₂/km → 0.12 g/m
        if (meters < 0.01)
            return `${(meters * 100).toFixed(2)} mm driven by car`;
        if (meters < 1)
            return `${(meters * 100).toFixed(1)} cm driven by car`;
        if (meters < 1000)
            return `${meters.toFixed(1)} m driven by car`;
        return `${(meters / 1000).toFixed(4)} km driven by car`;
    }
    _escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
    _setContent(html) {
        this.lastHtml = html;
        if (!this._webviewReady) {
            this._pendingContent = html;
            return;
        }
        this.panel?.webview.postMessage({ command: 'setContent', html });
    }
    _fallbackHtml() {
        return `<!DOCTYPE html><html><body style="font-family:sans-serif;padding:16px;background:#1e1e1e;color:#ccc">
      <h2>🌱 Carbon Optimizer</h2>
      <div id="content"></div>
      <script>
        const vscode = acquireVsCodeApi();
        vscode.postMessage({ command: 'ready' });
        document.addEventListener('click', e => {
          const t = e.target;
          if (!t) return;
          if (t.id === 'optimize-btn') vscode.postMessage({ command: 'optimize' });
          if (t.id === 'copy-btn') {
            const el = document.getElementById('optimized-code');
            if (el) vscode.postMessage({ command: 'copy', code: el.textContent || '' });
          }
          if (t.id === 'apply-btn') {
            const el = document.getElementById('optimized-code');
            if (el) { t.disabled = true; t.textContent = 'Applying…'; vscode.postMessage({ command: 'apply', code: el.textContent || '' }); }
          }
        });
        window.addEventListener('message', e => {
          const m = e.data;
          if (m.command === 'setContent') document.getElementById('content').innerHTML = m.html;
          if (m.command === 'copyResult') { const b = document.getElementById('copy-btn'); if(b){const o=b.textContent;b.textContent='✓ Copied!';setTimeout(()=>{b.textContent=o;},2000);} }
          if (m.command === 'applyResult') { const b = document.getElementById('apply-btn'); if(b){b.disabled=false;b.textContent=e.data.success?'✓ Applied!':'↙ Apply to File';if(e.data.success)setTimeout(()=>{b.textContent='↙ Apply to File';},3000);} }
        });
      </script>
    </body></html>`;
    }
    dispose() {
        this.panel?.dispose();
    }
}
exports.ReportPanel = ReportPanel;
//# sourceMappingURL=reportPanel.js.map