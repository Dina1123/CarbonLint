"use strict";
/**
 * Manual mock for the 'vscode' module.
 * Used by Jest tests to avoid requiring the VS Code extension host.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConfigurationTarget = exports.StatusBarAlignment = exports.ViewColumn = exports.MockTextDocument = exports.MockExtensionContext = exports.commands = exports.languages = exports.workspace = exports.window = exports.MarkdownString = exports.Hover = exports.MockWebviewPanel = exports.MockOutputChannel = exports.MockStatusBarItem = exports.Uri = exports.MockDiagnosticCollection = exports.Diagnostic = exports.Range = exports.Position = exports.DiagnosticSeverity = void 0;
// ─── DiagnosticSeverity ───────────────────────────────────────────────────────
var DiagnosticSeverity;
(function (DiagnosticSeverity) {
    DiagnosticSeverity[DiagnosticSeverity["Error"] = 0] = "Error";
    DiagnosticSeverity[DiagnosticSeverity["Warning"] = 1] = "Warning";
    DiagnosticSeverity[DiagnosticSeverity["Information"] = 2] = "Information";
    DiagnosticSeverity[DiagnosticSeverity["Hint"] = 3] = "Hint";
})(DiagnosticSeverity || (exports.DiagnosticSeverity = DiagnosticSeverity = {}));
// ─── Range & Position ─────────────────────────────────────────────────────────
class Position {
    constructor(line, character) {
        this.line = line;
        this.character = character;
    }
}
exports.Position = Position;
class Range {
    constructor(start, end) {
        this.start = start;
        this.end = end;
    }
}
exports.Range = Range;
// ─── Diagnostic ───────────────────────────────────────────────────────────────
class Diagnostic {
    constructor(range, message, severity = DiagnosticSeverity.Error) {
        this.range = range;
        this.message = message;
        this.severity = severity;
    }
}
exports.Diagnostic = Diagnostic;
// ─── DiagnosticCollection ─────────────────────────────────────────────────────
class MockDiagnosticCollection {
    constructor() {
        this._map = new Map();
    }
    set(uri, diagnostics) {
        this._map.set(uri.toString(), diagnostics);
    }
    delete(uri) {
        this._map.delete(uri.toString());
    }
    clear() {
        this._map.clear();
    }
    get(uri) {
        return this._map.get(uri.toString());
    }
    has(uri) {
        return this._map.has(uri.toString());
    }
    dispose() {
        this._map.clear();
    }
}
exports.MockDiagnosticCollection = MockDiagnosticCollection;
// ─── Uri ──────────────────────────────────────────────────────────────────────
class Uri {
    constructor(scheme, path) {
        this.scheme = scheme;
        this.path = path;
    }
    static file(path) {
        return new Uri('file', path);
    }
    toString() {
        return `${this.scheme}://${this.path}`;
    }
}
exports.Uri = Uri;
// ─── StatusBarItem ────────────────────────────────────────────────────────────
class MockStatusBarItem {
    constructor() {
        this.text = '';
        this.tooltip = '';
        this.command = '';
        this.show = jest.fn();
        this.hide = jest.fn();
        this.dispose = jest.fn();
    }
}
exports.MockStatusBarItem = MockStatusBarItem;
// ─── OutputChannel ────────────────────────────────────────────────────────────
class MockOutputChannel {
    constructor(name) {
        this.lines = [];
        this.show = jest.fn();
        this.hide = jest.fn();
        this.dispose = jest.fn();
        this.name = name;
    }
    appendLine(value) {
        this.lines.push(value);
    }
    append(value) {
        this.lines.push(value);
    }
    clear() { this.lines = []; }
}
exports.MockOutputChannel = MockOutputChannel;
// ─── WebviewPanel ─────────────────────────────────────────────────────────────
class MockWebviewPanel {
    constructor() {
        this.webview = {
            html: '',
            onDidReceiveMessage: jest.fn(),
            postMessage: jest.fn(),
            asWebviewUri: jest.fn((uri) => uri),
            cspSource: 'mock-csp',
        };
        this.onDidDispose = jest.fn();
        this.reveal = jest.fn();
        this.dispose = jest.fn();
        this.visible = true;
        this.active = true;
        this.title = '';
    }
}
exports.MockWebviewPanel = MockWebviewPanel;
// ─── Hover ────────────────────────────────────────────────────────────────────
class Hover {
    constructor(contents) {
        this.contents = contents;
    }
}
exports.Hover = Hover;
// ─── MarkdownString ───────────────────────────────────────────────────────────
class MarkdownString {
    constructor(value = '') {
        this.value = value;
    }
    appendMarkdown(text) {
        this.value += text;
        return this;
    }
}
exports.MarkdownString = MarkdownString;
// ─── window ───────────────────────────────────────────────────────────────────
exports.window = {
    showInformationMessage: jest.fn(),
    showWarningMessage: jest.fn(),
    showErrorMessage: jest.fn(),
    createStatusBarItem: jest.fn(() => new MockStatusBarItem()),
    createOutputChannel: jest.fn((name) => new MockOutputChannel(name)),
    createWebviewPanel: jest.fn(() => new MockWebviewPanel()),
    activeTextEditor: undefined,
    onDidChangeActiveTextEditor: jest.fn(),
};
// ─── workspace ────────────────────────────────────────────────────────────────
exports.workspace = {
    onDidSaveTextDocument: jest.fn(),
    onDidCloseTextDocument: jest.fn(),
    onDidChangeWorkspaceFolders: jest.fn(),
    onDidChangeConfiguration: jest.fn(),
    workspaceFolders: [],
    getConfiguration: jest.fn(() => ({
        get: jest.fn((key, defaultValue) => {
            if (key === 'pythonPath')
                return 'python3';
            return defaultValue;
        }),
    })),
};
// ─── languages ────────────────────────────────────────────────────────────────
exports.languages = {
    createDiagnosticCollection: jest.fn(() => new MockDiagnosticCollection()),
    registerHoverProvider: jest.fn(),
};
// ─── commands ─────────────────────────────────────────────────────────────────
exports.commands = {
    registerCommand: jest.fn(),
    executeCommand: jest.fn(),
};
// ─── ExtensionContext ─────────────────────────────────────────────────────────
class MockExtensionContext {
    constructor() {
        this.subscriptions = [];
        this.extensionPath = '/mock/extension/path';
        this.extensionUri = Uri.file('/mock/extension/path');
        this.globalState = {
            get: jest.fn(),
            update: jest.fn(),
            keys: jest.fn(() => []),
        };
        this.workspaceState = {
            get: jest.fn(),
            update: jest.fn(),
            keys: jest.fn(() => []),
        };
    }
    asAbsolutePath(relativePath) {
        return `/mock/extension/path/${relativePath}`;
    }
}
exports.MockExtensionContext = MockExtensionContext;
// ─── TextDocument mock helper ─────────────────────────────────────────────────
class MockTextDocument {
    constructor(uri, languageId, getText, lineCount = 10) {
        this.uri = uri;
        this.languageId = languageId;
        this.getText = getText;
        this.lineCount = lineCount;
    }
    lineAt(line) {
        return {
            text: `line ${line}`,
            range: new Range(new Position(line, 0), new Position(line, 10)),
        };
    }
}
exports.MockTextDocument = MockTextDocument;
// ─── ViewColumn ───────────────────────────────────────────────────────────────
var ViewColumn;
(function (ViewColumn) {
    ViewColumn[ViewColumn["Active"] = -1] = "Active";
    ViewColumn[ViewColumn["Beside"] = -2] = "Beside";
    ViewColumn[ViewColumn["One"] = 1] = "One";
    ViewColumn[ViewColumn["Two"] = 2] = "Two";
    ViewColumn[ViewColumn["Three"] = 3] = "Three";
})(ViewColumn || (exports.ViewColumn = ViewColumn = {}));
// ─── StatusBarAlignment ───────────────────────────────────────────────────────
var StatusBarAlignment;
(function (StatusBarAlignment) {
    StatusBarAlignment[StatusBarAlignment["Left"] = 1] = "Left";
    StatusBarAlignment[StatusBarAlignment["Right"] = 2] = "Right";
})(StatusBarAlignment || (exports.StatusBarAlignment = StatusBarAlignment = {}));
// ─── ConfigurationTarget ─────────────────────────────────────────────────────
var ConfigurationTarget;
(function (ConfigurationTarget) {
    ConfigurationTarget[ConfigurationTarget["Global"] = 1] = "Global";
    ConfigurationTarget[ConfigurationTarget["Workspace"] = 2] = "Workspace";
    ConfigurationTarget[ConfigurationTarget["WorkspaceFolder"] = 3] = "WorkspaceFolder";
})(ConfigurationTarget || (exports.ConfigurationTarget = ConfigurationTarget = {}));
//# sourceMappingURL=vscode.js.map