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
exports.ConfigScanner = void 0;
const vscode = __importStar(require("vscode"));
class ConfigScanner {
    constructor(bridge, reportPanel) {
        this.bridge = bridge;
        this.reportPanel = reportPanel;
        /** Set of workspace folder URI strings already scanned this session. */
        this.hasScanned = new Set();
        this.outputChannel = vscode.window.createOutputChannel('Carbon Optimizer');
    }
    /**
     * Register workspace folder listeners and scan any already-open folders.
     * Called once on extension activation.
     */
    register(context) {
        // Scan folders that are already open when the extension activates
        const folders = vscode.workspace.workspaceFolders ?? [];
        for (const folder of folders) {
            this.scan(folder.uri.fsPath, folder.uri.toString());
        }
        // Scan newly added workspace folders
        context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders((event) => {
            for (const folder of event.added) {
                this.scan(folder.uri.fsPath, folder.uri.toString());
            }
        }));
    }
    /**
     * Run the config scan for a workspace root path.
     * Skips if this folder has already been scanned this session.
     * Runs asynchronously so workspace startup is not delayed.
     */
    scan(workspaceRoot, folderKey) {
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
    async _doScan(workspaceRoot) {
        try {
            const issues = await this.bridge.call('analyze_configs', {
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
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.outputChannel.appendLine(`[Carbon Optimizer] Config scan failed: ${message}`);
            // Do not show a notification — log only
        }
    }
    dispose() {
        // Nothing to clean up — subscriptions are managed by context.subscriptions
    }
}
exports.ConfigScanner = ConfigScanner;
//# sourceMappingURL=configScanner.js.map