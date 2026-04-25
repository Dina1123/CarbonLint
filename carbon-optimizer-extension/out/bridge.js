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
exports.Bridge = void 0;
const child_process_1 = require("child_process");
const uuid_1 = require("uuid");
const vscode = __importStar(require("vscode"));
class Bridge {
    constructor(pythonPath, serverScriptPath, outputChannel) {
        this.pythonPath = pythonPath;
        this.serverScriptPath = serverScriptPath;
        this.process = null;
        this.pending = new Map();
        this.restartCount = 0;
        this.buffer = '';
        this.disposed = false;
        this.MAX_RESTARTS = 3;
        this.outputChannel = outputChannel ?? vscode.window.createOutputChannel('Carbon Optimizer');
    }
    async start() {
        if (this.disposed)
            return;
        this.process = (0, child_process_1.spawn)(this.pythonPath, [this.serverScriptPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
        });
        this.buffer = '';
        // Handle stdout — accumulate lines and dispatch responses
        this.process.stdout?.on('data', (chunk) => {
            this.buffer += chunk.toString();
            const lines = this.buffer.split('\n');
            // Keep the last (potentially incomplete) line in the buffer
            this.buffer = lines.pop() ?? '';
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed)
                    continue;
                this._handleLine(trimmed);
            }
        });
        // Log stderr to output channel
        this.process.stderr?.on('data', (chunk) => {
            this.outputChannel.appendLine(`[Backend stderr] ${chunk.toString().trim()}`);
        });
        // Handle process exit — restart if under limit
        this.process.on('close', (code) => {
            if (this.disposed)
                return;
            this.outputChannel.appendLine(`[Backend] Process exited with code ${code}`);
            if (this.restartCount < this.MAX_RESTARTS) {
                this.restartCount++;
                this.outputChannel.appendLine(`[Backend] Restarting (attempt ${this.restartCount}/${this.MAX_RESTARTS})...`);
                this.start();
            }
            else {
                const msg = `Carbon Optimizer backend failed to start after ${this.MAX_RESTARTS} attempts.`;
                vscode.window.showErrorMessage(msg);
                // Reject all pending promises
                for (const [, { reject }] of this.pending) {
                    reject(new Error(msg));
                }
                this.pending.clear();
            }
        });
    }
    call(method, params) {
        return new Promise((resolve, reject) => {
            if (!this.process || this.process.killed || this.disposed) {
                reject(new Error('Backend process is not running'));
                return;
            }
            const id = (0, uuid_1.v4)();
            const request = { id, method, params };
            this.pending.set(id, {
                resolve: (value) => resolve(value),
                reject,
            });
            const line = JSON.stringify(request) + '\n';
            this.process.stdin?.write(line, (err) => {
                if (err) {
                    this.pending.delete(id);
                    reject(err);
                }
            });
        });
    }
    _handleLine(line) {
        let response;
        try {
            response = JSON.parse(line);
        }
        catch (e) {
            this.outputChannel.appendLine(`[Backend] Failed to parse response: ${line}`);
            return;
        }
        const pending = this.pending.get(response.id);
        if (!pending) {
            this.outputChannel.appendLine(`[Backend] No pending request for id: ${response.id}`);
            return;
        }
        this.pending.delete(response.id);
        // Reset restart counter on first successful response
        if (response.result !== undefined) {
            this.restartCount = 0;
        }
        if (response.error) {
            pending.reject(new Error(`${response.error.type}: ${response.error.message}`));
        }
        else {
            pending.resolve(response.result);
        }
    }
    dispose() {
        this.disposed = true;
        // Reject all pending promises
        for (const [, { reject }] of this.pending) {
            reject(new Error('Bridge disposed'));
        }
        this.pending.clear();
        if (this.process && !this.process.killed) {
            this.process.kill();
        }
        this.process = null;
    }
}
exports.Bridge = Bridge;
//# sourceMappingURL=bridge.js.map