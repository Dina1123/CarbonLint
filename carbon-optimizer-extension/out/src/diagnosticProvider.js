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
exports.DiagnosticProvider = void 0;
exports.mapSeverity = mapSeverity;
const vscode = __importStar(require("vscode"));
function mapSeverity(severity) {
    switch (severity) {
        case 'HIGH': return vscode.DiagnosticSeverity.Error;
        case 'MEDIUM': return vscode.DiagnosticSeverity.Warning;
        case 'LOW': return vscode.DiagnosticSeverity.Information;
        default: return vscode.DiagnosticSeverity.Information;
    }
}
class DiagnosticProvider {
    constructor(bridge) {
        this.bridge = bridge;
        // Store issues per URI for hover provider access
        this.issueMap = new Map();
        this.collection = vscode.languages.createDiagnosticCollection('carbon-optimizer');
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
        this.outputChannel = vscode.window.createOutputChannel('Carbon Optimizer');
    }
    register(context) {
        context.subscriptions.push(vscode.workspace.onDidSaveTextDocument((doc) => {
            if (doc.languageId === 'python') {
                this.onSave(doc);
            }
        }), vscode.workspace.onDidCloseTextDocument((doc) => {
            this.onClose(doc);
        }), this.collection, this.statusBarItem);
    }
    async onSave(document) {
        this.statusBarItem.text = '$(sync~spin) Carbon: Analyzing…';
        this.statusBarItem.show();
        try {
            const result = await this.bridge.call('analyze_efficiency', {
                code: document.getText(),
            });
            const diagnostics = this.toDiagnostics(result.issues, document);
            this.collection.set(document.uri, diagnostics);
            this.issueMap.set(document.uri.toString(), result.issues);
            const count = result.issues.length;
            this.statusBarItem.text = count === 0
                ? '$(check) Carbon: No issues'
                : `$(warning) Carbon: ${count} issue${count === 1 ? '' : 's'}`;
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.outputChannel.appendLine(`[Carbon Optimizer] Analysis error: ${message}`);
            this.collection.delete(document.uri);
            this.issueMap.delete(document.uri.toString());
            this.statusBarItem.text = '$(error) Carbon: Error';
        }
    }
    onClose(document) {
        this.collection.delete(document.uri);
        this.issueMap.delete(document.uri.toString());
    }
    toDiagnostics(issues, document) {
        return issues.map((issue) => {
            const lineIndex = Math.max(0, issue.line_number - 1);
            const lineText = document.lineAt(lineIndex).text;
            const range = new vscode.Range(new vscode.Position(lineIndex, 0), new vscode.Position(lineIndex, lineText.length));
            const diagnostic = new vscode.Diagnostic(range, issue.description, mapSeverity(issue.severity));
            diagnostic.source = 'Carbon Optimizer';
            diagnostic.code = issue.suggested_fix;
            return diagnostic;
        });
    }
    getIssuesForUri(uri) {
        return this.issueMap.get(uri.toString()) ?? [];
    }
    dispose() {
        this.collection.dispose();
        this.statusBarItem.dispose();
    }
}
exports.DiagnosticProvider = DiagnosticProvider;
//# sourceMappingURL=diagnosticProvider.js.map