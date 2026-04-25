/**
 * Manual mock for the 'vscode' module.
 * Used by Jest tests to avoid requiring the VS Code extension host.
 */

// ─── DiagnosticSeverity ───────────────────────────────────────────────────────

export enum DiagnosticSeverity {
  Error = 0,
  Warning = 1,
  Information = 2,
  Hint = 3,
}

// ─── Range & Position ─────────────────────────────────────────────────────────

export class Position {
  constructor(public readonly line: number, public readonly character: number) {}
}

export class Range {
  constructor(
    public readonly start: Position,
    public readonly end: Position,
  ) {}
}

// ─── Diagnostic ───────────────────────────────────────────────────────────────

export class Diagnostic {
  public source?: string;
  public code?: string | number;

  constructor(
    public readonly range: Range,
    public readonly message: string,
    public readonly severity: DiagnosticSeverity = DiagnosticSeverity.Error,
  ) {}
}

// ─── DiagnosticCollection ─────────────────────────────────────────────────────

export class MockDiagnosticCollection {
  private _map = new Map<string, Diagnostic[]>();

  set(uri: Uri, diagnostics: Diagnostic[]): void {
    this._map.set(uri.toString(), diagnostics);
  }

  delete(uri: Uri): void {
    this._map.delete(uri.toString());
  }

  clear(): void {
    this._map.clear();
  }

  get(uri: Uri): Diagnostic[] | undefined {
    return this._map.get(uri.toString());
  }

  has(uri: Uri): boolean {
    return this._map.has(uri.toString());
  }

  dispose(): void {
    this._map.clear();
  }
}

// ─── Uri ──────────────────────────────────────────────────────────────────────

export class Uri {
  private constructor(
    public readonly scheme: string,
    public readonly path: string,
  ) {}

  static file(path: string): Uri {
    return new Uri('file', path);
  }

  toString(): string {
    return `${this.scheme}://${this.path}`;
  }
}

// ─── StatusBarItem ────────────────────────────────────────────────────────────

export class MockStatusBarItem {
  text = '';
  tooltip = '';
  command = '';
  show = jest.fn();
  hide = jest.fn();
  dispose = jest.fn();
}

// ─── OutputChannel ────────────────────────────────────────────────────────────

export class MockOutputChannel {
  name: string;
  lines: string[] = [];

  constructor(name: string) {
    this.name = name;
  }

  appendLine(value: string): void {
    this.lines.push(value);
  }

  append(value: string): void {
    this.lines.push(value);
  }

  show = jest.fn();
  hide = jest.fn();
  dispose = jest.fn();
  clear(): void { this.lines = []; }
}

// ─── WebviewPanel ─────────────────────────────────────────────────────────────

export class MockWebviewPanel {
  webview = {
    html: '',
    onDidReceiveMessage: jest.fn(),
    postMessage: jest.fn(),
    asWebviewUri: jest.fn((uri: Uri) => uri),
    cspSource: 'mock-csp',
  };
  onDidDispose = jest.fn();
  reveal = jest.fn();
  dispose = jest.fn();
  visible = true;
  active = true;
  title = '';
}

// ─── Hover ────────────────────────────────────────────────────────────────────

export class Hover {
  constructor(public readonly contents: string | { value: string }) {}
}

// ─── MarkdownString ───────────────────────────────────────────────────────────

export class MarkdownString {
  value: string;
  constructor(value = '') {
    this.value = value;
  }
  appendMarkdown(text: string): this {
    this.value += text;
    return this;
  }
}

// ─── window ───────────────────────────────────────────────────────────────────

export const window = {
  showInformationMessage: jest.fn(),
  showWarningMessage: jest.fn(),
  showErrorMessage: jest.fn(),
  createStatusBarItem: jest.fn(() => new MockStatusBarItem()),
  createOutputChannel: jest.fn((name: string) => new MockOutputChannel(name)),
  createWebviewPanel: jest.fn(() => new MockWebviewPanel()),
  activeTextEditor: undefined as { document: MockTextDocument } | undefined,
  onDidChangeActiveTextEditor: jest.fn(),
};

// ─── workspace ────────────────────────────────────────────────────────────────

export const workspace = {
  onDidSaveTextDocument: jest.fn(),
  onDidCloseTextDocument: jest.fn(),
  onDidChangeWorkspaceFolders: jest.fn(),
  onDidChangeConfiguration: jest.fn(),
  workspaceFolders: [] as Array<{ uri: Uri; name: string; index: number }>,
  getConfiguration: jest.fn(() => ({
    get: jest.fn((key: string, defaultValue?: unknown) => {
      if (key === 'pythonPath') return 'python3';
      return defaultValue;
    }),
  })),
};

// ─── languages ────────────────────────────────────────────────────────────────

export const languages = {
  createDiagnosticCollection: jest.fn(() => new MockDiagnosticCollection()),
  registerHoverProvider: jest.fn(),
};

// ─── commands ─────────────────────────────────────────────────────────────────

export const commands = {
  registerCommand: jest.fn(),
  executeCommand: jest.fn(),
};

// ─── ExtensionContext ─────────────────────────────────────────────────────────

export class MockExtensionContext {
  subscriptions: { dispose(): void }[] = [];
  extensionPath = '/mock/extension/path';
  extensionUri = Uri.file('/mock/extension/path');
  globalState = {
    get: jest.fn(),
    update: jest.fn(),
    keys: jest.fn(() => []),
  };
  workspaceState = {
    get: jest.fn(),
    update: jest.fn(),
    keys: jest.fn(() => []),
  };
  asAbsolutePath(relativePath: string): string {
    return `/mock/extension/path/${relativePath}`;
  }
}

// ─── TextDocument mock helper ─────────────────────────────────────────────────

export class MockTextDocument {
  constructor(
    public readonly uri: Uri,
    public readonly languageId: string,
    public readonly getText: () => string,
    public readonly lineCount: number = 10,
  ) {}

  lineAt(line: number) {
    return {
      text: `line ${line}`,
      range: new Range(new Position(line, 0), new Position(line, 10)),
    };
  }
}

// ─── ViewColumn ───────────────────────────────────────────────────────────────

export enum ViewColumn {
  Active = -1,
  Beside = -2,
  One = 1,
  Two = 2,
  Three = 3,
}

// ─── StatusBarAlignment ───────────────────────────────────────────────────────

export enum StatusBarAlignment {
  Left = 1,
  Right = 2,
}

// ─── ConfigurationTarget ─────────────────────────────────────────────────────

export enum ConfigurationTarget {
  Global = 1,
  Workspace = 2,
  WorkspaceFolder = 3,
}
