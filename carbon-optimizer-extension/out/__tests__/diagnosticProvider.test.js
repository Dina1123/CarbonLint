"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const diagnosticProvider_1 = require("../diagnosticProvider");
const vscode_1 = require("../../__mocks__/vscode");
// Helper to create a mock document
function makeDoc(code, uri = vscode_1.Uri.file('/test/app.py')) {
    const lines = code.split('\n');
    return new vscode_1.MockTextDocument(uri, 'python', () => code, lines.length);
}
// Helper to create an Issue
function makeIssue(overrides = {}) {
    return {
        issue_id: 'nested-loop-L5',
        severity: 'HIGH',
        line_number: 5,
        description: 'Nested loop detected.',
        suggested_fix: 'Use itertools.product',
        carbon_impact_score: 'HIGH',
        ...overrides,
    };
}
describe('mapSeverity', () => {
    test('HIGH maps to Error', () => {
        expect((0, diagnosticProvider_1.mapSeverity)('HIGH')).toBe(vscode_1.DiagnosticSeverity.Error);
    });
    test('MEDIUM maps to Warning', () => {
        expect((0, diagnosticProvider_1.mapSeverity)('MEDIUM')).toBe(vscode_1.DiagnosticSeverity.Warning);
    });
    test('LOW maps to Information', () => {
        expect((0, diagnosticProvider_1.mapSeverity)('LOW')).toBe(vscode_1.DiagnosticSeverity.Information);
    });
    test('unknown severity maps to Information', () => {
        expect((0, diagnosticProvider_1.mapSeverity)('UNKNOWN')).toBe(vscode_1.DiagnosticSeverity.Information);
    });
});
describe('DiagnosticProvider.toDiagnostics', () => {
    let provider;
    let mockBridge;
    beforeEach(() => {
        mockBridge = { call: jest.fn(), start: jest.fn(), dispose: jest.fn() };
        provider = new diagnosticProvider_1.DiagnosticProvider(mockBridge);
    });
    test('converts HIGH issue to Error diagnostic', () => {
        const doc = makeDoc('for i in range(10):\n    for j in range(10):\n        pass\n    pass\n    pass');
        const issues = [makeIssue({ severity: 'HIGH', line_number: 2 })];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics).toHaveLength(1);
        expect(diagnostics[0].severity).toBe(vscode_1.DiagnosticSeverity.Error);
    });
    test('converts MEDIUM issue to Warning diagnostic', () => {
        const doc = makeDoc('x = 1\n');
        const issues = [makeIssue({ severity: 'MEDIUM', line_number: 1 })];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics[0].severity).toBe(vscode_1.DiagnosticSeverity.Warning);
    });
    test('converts LOW issue to Information diagnostic', () => {
        const doc = makeDoc('x = 1\n');
        const issues = [makeIssue({ severity: 'LOW', line_number: 1 })];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics[0].severity).toBe(vscode_1.DiagnosticSeverity.Information);
    });
    test('sets source to "Carbon Optimizer"', () => {
        const doc = makeDoc('x = 1\n');
        const issues = [makeIssue({ line_number: 1 })];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics[0].source).toBe('Carbon Optimizer');
    });
    test('sets code to suggested_fix', () => {
        const doc = makeDoc('x = 1\n');
        const issues = [makeIssue({ line_number: 1, suggested_fix: 'Use set lookup' })];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics[0].code).toBe('Use set lookup');
    });
    test('sets message to issue description', () => {
        const doc = makeDoc('x = 1\n');
        const issues = [makeIssue({ line_number: 1, description: 'Nested loop detected.' })];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics[0].message).toBe('Nested loop detected.');
    });
    test('returns empty array for empty issues list', () => {
        const doc = makeDoc('x = 1\n');
        const diagnostics = provider.toDiagnostics([], doc);
        expect(diagnostics).toHaveLength(0);
    });
    test('handles multiple issues', () => {
        const doc = makeDoc('x = 1\ny = 2\nz = 3\n');
        const issues = [
            makeIssue({ line_number: 1, severity: 'HIGH' }),
            makeIssue({ line_number: 2, severity: 'MEDIUM' }),
            makeIssue({ line_number: 3, severity: 'LOW' }),
        ];
        const diagnostics = provider.toDiagnostics(issues, doc);
        expect(diagnostics).toHaveLength(3);
        expect(diagnostics[0].severity).toBe(vscode_1.DiagnosticSeverity.Error);
        expect(diagnostics[1].severity).toBe(vscode_1.DiagnosticSeverity.Warning);
        expect(diagnostics[2].severity).toBe(vscode_1.DiagnosticSeverity.Information);
    });
});
//# sourceMappingURL=diagnosticProvider.test.js.map