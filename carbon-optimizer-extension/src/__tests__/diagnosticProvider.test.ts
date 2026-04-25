import { DiagnosticProvider, mapSeverity, Issue } from '../diagnosticProvider';
import { DiagnosticSeverity, MockDiagnosticCollection, Uri, MockTextDocument, Position, Range, MockExtensionContext } from '../../__mocks__/vscode';
import * as vscode from 'vscode';

// Helper to create a mock document
function makeDoc(code: string, uri = Uri.file('/test/app.py')) {
  const lines = code.split('\n');
  return new MockTextDocument(uri, 'python', () => code, lines.length);
}

// Helper to create an Issue
function makeIssue(overrides: Partial<Issue> = {}): Issue {
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
    expect(mapSeverity('HIGH')).toBe(DiagnosticSeverity.Error);
  });

  test('MEDIUM maps to Warning', () => {
    expect(mapSeverity('MEDIUM')).toBe(DiagnosticSeverity.Warning);
  });

  test('LOW maps to Information', () => {
    expect(mapSeverity('LOW')).toBe(DiagnosticSeverity.Information);
  });

  test('unknown severity maps to Information', () => {
    expect(mapSeverity('UNKNOWN')).toBe(DiagnosticSeverity.Information);
  });
});

describe('DiagnosticProvider.toDiagnostics', () => {
  let provider: DiagnosticProvider;
  let mockBridge: any;

  beforeEach(() => {
    mockBridge = { call: jest.fn(), start: jest.fn(), dispose: jest.fn() };
    provider = new DiagnosticProvider(mockBridge);
  });

  test('converts HIGH issue to Error diagnostic', () => {
    const doc = makeDoc('for i in range(10):\n    for j in range(10):\n        pass\n    pass\n    pass');
    const issues = [makeIssue({ severity: 'HIGH', line_number: 2 })];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics).toHaveLength(1);
    expect(diagnostics[0].severity).toBe(DiagnosticSeverity.Error);
  });

  test('converts MEDIUM issue to Warning diagnostic', () => {
    const doc = makeDoc('x = 1\n');
    const issues = [makeIssue({ severity: 'MEDIUM', line_number: 1 })];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics[0].severity).toBe(DiagnosticSeverity.Warning);
  });

  test('converts LOW issue to Information diagnostic', () => {
    const doc = makeDoc('x = 1\n');
    const issues = [makeIssue({ severity: 'LOW', line_number: 1 })];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics[0].severity).toBe(DiagnosticSeverity.Information);
  });

  test('sets source to "Carbon Optimizer"', () => {
    const doc = makeDoc('x = 1\n');
    const issues = [makeIssue({ line_number: 1 })];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics[0].source).toBe('Carbon Optimizer');
  });

  test('sets code to suggested_fix', () => {
    const doc = makeDoc('x = 1\n');
    const issues = [makeIssue({ line_number: 1, suggested_fix: 'Use set lookup' })];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics[0].code).toBe('Use set lookup');
  });

  test('sets message to issue description', () => {
    const doc = makeDoc('x = 1\n');
    const issues = [makeIssue({ line_number: 1, description: 'Nested loop detected.' })];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics[0].message).toBe('Nested loop detected.');
  });

  test('returns empty array for empty issues list', () => {
    const doc = makeDoc('x = 1\n');
    const diagnostics = provider.toDiagnostics([], doc as any);
    expect(diagnostics).toHaveLength(0);
  });

  test('handles multiple issues', () => {
    const doc = makeDoc('x = 1\ny = 2\nz = 3\n');
    const issues = [
      makeIssue({ line_number: 1, severity: 'HIGH' }),
      makeIssue({ line_number: 2, severity: 'MEDIUM' }),
      makeIssue({ line_number: 3, severity: 'LOW' }),
    ];
    const diagnostics = provider.toDiagnostics(issues, doc as any);
    expect(diagnostics).toHaveLength(3);
    expect(diagnostics[0].severity).toBe(DiagnosticSeverity.Error);
    expect(diagnostics[1].severity).toBe(DiagnosticSeverity.Warning);
    expect(diagnostics[2].severity).toBe(DiagnosticSeverity.Information);
  });
});
