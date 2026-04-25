import { ChildProcess, spawn } from 'child_process';
import { v4 as uuidv4 } from 'uuid';
import * as vscode from 'vscode';

export interface BridgeRequest {
  id: string;
  method: string;
  params: Record<string, unknown>;
}

export interface BridgeError {
  message: string;
  type: string;
}

export interface BridgeResponse {
  id: string;
  result?: unknown;
  error?: BridgeError;
}

export class Bridge {
  private process: ChildProcess | null = null;
  private pending = new Map<string, { resolve: (value: unknown) => void; reject: (reason: unknown) => void }>();
  private restartCount = 0;
  private outputChannel: vscode.OutputChannel;
  private buffer = '';
  private disposed = false;

  readonly MAX_RESTARTS = 3;

  constructor(
    private readonly pythonPath: string,
    private readonly serverScriptPath: string,
    outputChannel?: vscode.OutputChannel,
  ) {
    this.outputChannel = outputChannel ?? vscode.window.createOutputChannel('Carbon Optimizer');
  }

  async start(): Promise<void> {
    if (this.disposed) return;

    this.process = spawn(this.pythonPath, [this.serverScriptPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    this.buffer = '';

    // Handle stdout — accumulate lines and dispatch responses
    this.process.stdout?.on('data', (chunk: Buffer) => {
      this.buffer += chunk.toString();
      const lines = this.buffer.split('\n');
      // Keep the last (potentially incomplete) line in the buffer
      this.buffer = lines.pop() ?? '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        this._handleLine(trimmed);
      }
    });

    // Log stderr to output channel
    this.process.stderr?.on('data', (chunk: Buffer) => {
      this.outputChannel.appendLine(`[Backend stderr] ${chunk.toString().trim()}`);
    });

    // Handle process exit — restart if under limit
    this.process.on('close', (code) => {
      if (this.disposed) return;
      this.outputChannel.appendLine(`[Backend] Process exited with code ${code}`);
      if (this.restartCount < this.MAX_RESTARTS) {
        this.restartCount++;
        this.outputChannel.appendLine(`[Backend] Restarting (attempt ${this.restartCount}/${this.MAX_RESTARTS})...`);
        this.start();
      } else {
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

  call<T>(method: string, params: Record<string, unknown>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      if (!this.process || this.process.killed || this.disposed) {
        reject(new Error('Backend process is not running'));
        return;
      }

      const id = uuidv4();
      const request: BridgeRequest = { id, method, params };

      this.pending.set(id, {
        resolve: (value) => resolve(value as T),
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

  private _handleLine(line: string): void {
    let response: BridgeResponse;
    try {
      response = JSON.parse(line) as BridgeResponse;
    } catch (e) {
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
    } else {
      pending.resolve(response.result);
    }
  }

  dispose(): void {
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
