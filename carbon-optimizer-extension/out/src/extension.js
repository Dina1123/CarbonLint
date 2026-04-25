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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const bridge_1 = require("./bridge");
const diagnosticProvider_1 = require("./diagnosticProvider");
const struggleTracker_1 = require("./struggleTracker");
const reportPanel_1 = require("./reportPanel");
const configScanner_1 = require("./configScanner");
let bridge;
async function activate(context) {
    // ── 1. Read configuration ────────────────────────────────────────────────
    const config = vscode.workspace.getConfiguration('carbonOptimizer');
    let pythonPath = config.get('pythonPath') ?? 'python3';
    // Resolve the backend server script path relative to the extension
    const serverScriptPath = path.join(context.extensionPath, '..', 'kiro-carbon-optimizer', 'backend_server.py');
    // ── 2. Instantiate components ────────────────────────────────────────────
    bridge = new bridge_1.Bridge(pythonPath, serverScriptPath);
    const diagnosticProvider = new diagnosticProvider_1.DiagnosticProvider(bridge);
    const struggleTracker = new struggleTracker_1.StruggleTracker();
    const reportPanel = new reportPanel_1.ReportPanel(bridge, context.extensionPath);
    const configScanner = new configScanner_1.ConfigScanner(bridge, reportPanel);
    // ── 3. Start the backend ─────────────────────────────────────────────────
    try {
        await bridge.start();
    }
    catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(`Carbon Optimizer: Failed to start backend. Check that Python is installed at "${pythonPath}". Error: ${message}`);
    }
    // ── 4. Register components ───────────────────────────────────────────────
    diagnosticProvider.register(context);
    configScanner.register(context);
    // ── 5. Register command: carbonOptimizer.openReport ──────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('carbonOptimizer.openReport', () => {
        const activeDoc = vscode.window.activeTextEditor?.document;
        reportPanel.show(activeDoc);
    }));
    // ── 6. Register HoverProvider for Python files ───────────────────────────
    context.subscriptions.push(vscode.languages.registerHoverProvider('python', {
        provideHover(document, position) {
            const issues = diagnosticProvider.getIssuesForUri(document.uri);
            const lineNumber = position.line + 1; // issues use 1-based line numbers
            const issue = issues.find((i) => i.line_number === lineNumber);
            if (!issue)
                return undefined;
            const md = new vscode.MarkdownString();
            md.appendMarkdown(`**Carbon Optimizer** — ${issue.description}\n\n`);
            md.appendMarkdown(`💡 **Suggested fix:** ${issue.suggested_fix}`);
            return new vscode.Hover(md);
        },
    }));
    // ── 7. Struggle detection on save ────────────────────────────────────────
    const outputChannel = vscode.window.createOutputChannel('Carbon Optimizer');
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (document) => {
        if (document.languageId !== 'python')
            return;
        const filePath = document.uri.fsPath;
        const triggered = struggleTracker.recordSave(filePath);
        if (triggered) {
            const filename = path.basename(filePath);
            vscode.window.showWarningMessage(`Carbon Optimizer: You've saved ${filename} 5 times in 10 minutes. ` +
                `You may be in an AI retry loop. Consider adding more context.`);
            // Notify the backend struggle detector
            try {
                const lineCount = document.lineCount;
                const signals = await bridge.call('on_edit_generated', {
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
            }
            catch {
                // Silently ignore backend errors for struggle detection
            }
            struggleTracker.reset(filePath);
        }
    }));
    // ── 8. React to pythonPath configuration changes ─────────────────────────
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(async (event) => {
        if (event.affectsConfiguration('carbonOptimizer.pythonPath')) {
            const newConfig = vscode.workspace.getConfiguration('carbonOptimizer');
            const newPythonPath = newConfig.get('pythonPath') ?? 'python3';
            bridge?.dispose();
            bridge = new bridge_1.Bridge(newPythonPath, serverScriptPath);
            try {
                await bridge.start();
            }
            catch (err) {
                const message = err instanceof Error ? err.message : String(err);
                vscode.window.showErrorMessage(`Carbon Optimizer: Failed to restart backend with new Python path "${newPythonPath}". Error: ${message}`);
            }
        }
    }));
}
function deactivate() {
    bridge?.dispose();
    bridge = undefined;
}
//# sourceMappingURL=extension.js.map