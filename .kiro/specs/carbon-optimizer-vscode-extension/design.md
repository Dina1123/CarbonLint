# Design Document: Carbon Optimizer VS Code Extension

## Overview

The Carbon Optimizer VS Code Extension is a TypeScript extension that surfaces the capabilities of the existing `kiro-carbon-optimizer` Python backend directly inside VS Code. It activates when a Python file is opened and provides four core features:

1. **Analyze on Save** — automatic efficiency analysis with inline diagnostics
2. **Sidebar Report Panel** — full optimization report with before/after metrics and code diff
3. **Config Scan on Workspace Open** — deployment config scanning for carbon-inefficient settings
4. **Struggle Detection** — save-frequency-based AI retry loop warnings

The extension communicates with the Python backend exclusively via a spawned child process using newline-delimited JSON over stdin/stdout. No HTTP server, no sockets — just a simple, reliable subprocess bridge.

### Key Design Decisions

- **Subprocess over HTTP**: Avoids port conflicts, firewall issues, and server lifecycle complexity. The backend process is owned entirely by the extension.
- **JSON-RPC style protocol**: Simple request/response matching by ID enables concurrent async calls without a full RPC framework.
- **No external WebView libraries**: The report panel uses plain HTML/CSS with no bundled JS frameworks, keeping the `.vsix` small and avoiding CSP issues.
- **StruggleTracker is extension-side only**: Save frequency tracking is done in TypeScript without a backend round-trip, keeping it fast and offline-capable.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     VS Code Extension Host                   │
│                                                             │
│  extension.ts (activation)                                  │
│       │                                                     │
│       ├── Bridge (bridge.ts)                                │
│       │     ├── spawns Python child process                 │
│       │     ├── writes JSON requests to stdin               │
│       │     └── reads JSON responses from stdout            │
│       │                                                     │
│       ├── DiagnosticProvider (diagnosticProvider.ts)        │
│       │     ├── subscribes to onDidSaveTextDocument         │
│       │     ├── calls Bridge.call('analyze_efficiency')     │
│       │     └── publishes VS Code Diagnostics               │
│       │                                                     │
│       ├── ReportPanel (reportPanel.ts)                      │
│       │     ├── VS Code WebView panel                       │
│       │     ├── calls Bridge.call('run_pipeline')           │
│       │     └── renders HTML report                         │
│       │                                                     │
│       ├── StruggleTracker (struggleTracker.ts)              │
│       │     ├── tracks per-file save timestamps             │
│       │     └── triggers warning at 5 saves / 10 min       │
│       │                                                     │
│       └── ConfigScanner (configScanner.ts)                  │
│             ├── runs on workspace open                      │
│             └── calls Bridge.call('analyze_configs')        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │ stdin/stdout (newline-delimited JSON)
┌─────────────────────────────────────────────────────────────┐
│                  Python Backend Process                      │
│                                                             │
│  backend_server.py                                          │
│       ├── reads JSON requests from stdin                    │
│       ├── dispatches to core tools                          │
│       │     ├── analyze_efficiency (tools/analyze.py)       │
│       │     ├── run_pipeline (tools/optimize.py)            │
│       │     ├── analyze_configs (core/config_analyzer.py)   │
│       │     └── on_edit_generated (core/struggle_detector)  │
│       └── writes JSON responses to stdout                   │
└─────────────────────────────────────────────────────────────┘
```

### Sequence: Analyze on Save

```
Developer saves file
      │
      ▼
DiagnosticProvider.onDidSaveTextDocument
      │
      ▼
Bridge.call('analyze_efficiency', {code})  ──► Python stdin
      │                                         │
      │                                    backend_server.py
      │                                    dispatches to analyze_efficiency()
      │                                         │
      ◄── JSON response {id, result} ──────────◄
      │
      ▼
DiagnosticProvider converts Issues → Diagnostics
      │
      ▼
vscode.languages.createDiagnosticCollection.set(uri, diagnostics)
```

---

## Components and Interfaces

### Bridge (`src/bridge.ts`)

Manages the Python subprocess lifecycle and all JSON communication.

```typescript
interface BridgeRequest {
  id: string;          // UUID v4
  method: string;      // 'analyze_efficiency' | 'run_pipeline' | 'analyze_configs' | 'on_edit_generated'
  params: Record<string, unknown>;
}

interface BridgeResponse {
  id: string;
  result?: unknown;
  error?: { message: string; type: string };
}

class Bridge {
  private process: ChildProcess | null;
  private pending: Map<string, { resolve: Function; reject: Function }>;
  private restartCount: number;
  private readonly MAX_RESTARTS = 3;

  constructor(pythonPath: string, serverScriptPath: string);

  /** Spawn the backend process. Called on activation and after restart. */
  start(): Promise<void>;

  /** Send a request and return a promise that resolves with the result or rejects with the error. */
  call<T>(method: string, params: Record<string, unknown>): Promise<T>;

  /** Terminate the backend process cleanly. */
  dispose(): void;
}
```

**Restart logic**: When the child process emits `close`, if `restartCount < MAX_RESTARTS`, Bridge increments the counter and calls `start()` again. After 3 failures it rejects all pending promises and shows a VS Code error notification. The counter resets to 0 after a successful response is received.

**Pending map**: Each `call()` generates a UUID, stores `{resolve, reject}` in `pending`, writes the request to stdin, and returns the promise. The stdout reader splits on `\n`, parses each line as JSON, looks up the ID in `pending`, and resolves or rejects accordingly.

### DiagnosticProvider (`src/diagnosticProvider.ts`)

```typescript
class DiagnosticProvider {
  private collection: vscode.DiagnosticCollection;
  private bridge: Bridge;

  constructor(bridge: Bridge);

  /** Called by extension.ts to register event listeners. */
  register(context: vscode.ExtensionContext): void;

  /** Triggered on onDidSaveTextDocument for Python files. */
  private async onSave(document: vscode.TextDocument): Promise<void>;

  /** Triggered on onDidCloseTextDocument. */
  private onClose(document: vscode.TextDocument): void;

  /** Convert AnalysisResult issues to VS Code Diagnostics. */
  private toDiagnostics(issues: Issue[], document: vscode.TextDocument): vscode.Diagnostic[];

  dispose(): void;
}
```

**Severity mapping**:
| Issue.severity | vscode.DiagnosticSeverity |
|---|---|
| `"HIGH"` | `Error` (0) |
| `"MEDIUM"` | `Warning` (1) |
| `"LOW"` | `Information` (2) |

Each `Diagnostic` targets the full text of the line at `issue.line_number - 1` (0-indexed). The `source` field is set to `"Carbon Optimizer"`. The `message` is `issue.description`. The `code` is set to `issue.suggested_fix` so it appears in the Problems panel.

### ReportPanel (`src/reportPanel.ts`)

```typescript
class ReportPanel {
  private panel: vscode.WebviewPanel | undefined;
  private bridge: Bridge;

  constructor(bridge: Bridge);

  /** Open or reveal the panel. */
  show(activeDocument?: vscode.TextDocument): void;

  /** Render a full Report into the WebView. */
  private renderReport(report: Report): string;

  /** Render a list of ConfigIssues into the WebView. */
  renderConfigIssues(issues: ConfigIssue[]): void;

  /** Render an error message into the WebView. */
  private renderError(message: string): string;

  dispose(): void;
}
```

The WebView HTML is loaded from `media/report.html` and uses `acquireVsCodeApi()` for message passing. The panel retains its last content when the user switches files (no auto-refresh on file change).

### StruggleTracker (`src/struggleTracker.ts`)

```typescript
class StruggleTracker {
  // Map<filePath, timestamp[]>
  private saveHistory: Map<string, number[]>;
  private readonly WINDOW_MS = 10 * 60 * 1000;  // 10 minutes
  private readonly THRESHOLD = 5;

  /** Record a save and return true if the struggle threshold is crossed. */
  recordSave(filePath: string): boolean;

  /** Reset the save history for a file (called after warning is shown). */
  reset(filePath: string): void;

  /** Return the count of saves within the sliding window for a file. */
  recentSaveCount(filePath: string, nowMs?: number): number;
}
```

`recordSave` appends `Date.now()` to the file's history, prunes entries older than `WINDOW_MS`, then returns `true` if the count reaches `THRESHOLD`. The caller (extension.ts) is responsible for showing the notification and calling `reset()`.

### ConfigScanner (`src/configScanner.ts`)

```typescript
class ConfigScanner {
  private bridge: Bridge;
  private hasScanned: Set<string>;  // workspace folder URIs already scanned

  constructor(bridge: Bridge);

  /** Register workspace folder open listener. Called once on activation. */
  register(context: vscode.ExtensionContext): void;

  /** Run the config scan for a workspace root path. */
  private async scan(workspaceRoot: string): Promise<void>;
}
```

`hasScanned` ensures the scan runs exactly once per workspace folder per extension session. It is populated on activation (for already-open folders) and on `onDidChangeWorkspaceFolders`.

---

## Data Models

These TypeScript interfaces mirror the Python dataclasses in `kiro-carbon-optimizer/core/models.py`.

```typescript
interface Issue {
  issue_id: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  line_number: number;
  description: string;
  suggested_fix: string;
  carbon_impact_score: string;
}

interface AnalysisResult {
  functions: FunctionInfo[];
  issues: Issue[];
  parse_time_ms: number;
}

interface Metrics {
  execution_time_ms: number;
  memory_used_bytes: number;
  energy_kwh: number;
  co2_grams: number;
}

interface Comparison {
  execution_time_improvement_pct: number;
  memory_improvement_pct: number;
  co2_improvement_pct: number;
  summary: string;
}

interface Report {
  analysis: AnalysisResult;
  original_metrics: Metrics;
  optimized_code: string;
  optimized_metrics: Metrics;
  comparison: Comparison;
}

interface ConfigIssue {
  issue_id: string;
  file_path: string;
  line_number: number;
  description: string;
  carbon_impact_score: string;
  remediation: string;
  example_fix: string;
}

interface StruggleSignal {
  signal_type: string;
  severity: string;
  message: string;
  mcp_suggestion?: { server: string; reason: string } | null;
}

interface BridgeError {
  message: string;
  type: string;
}
```

### Bridge Protocol

**Request** (written to Python stdin, one JSON object per line):
```json
{"id": "550e8400-e29b-41d4-a716-446655440000", "method": "analyze_efficiency", "params": {"code": "def foo(): pass\n"}}
{"id": "550e8400-e29b-41d4-a716-446655440001", "method": "run_pipeline", "params": {"code": "..."}}
{"id": "550e8400-e29b-41d4-a716-446655440002", "method": "analyze_configs", "params": {"workspace_root": "/home/user/project"}}
{"id": "550e8400-e29b-41d4-a716-446655440003", "method": "on_edit_generated", "params": {"file_path": "/home/user/project/main.py", "line_range": [1, 120]}}
```

**Response** (read from Python stdout, one JSON object per line):
```json
{"id": "550e8400-e29b-41d4-a716-446655440000", "result": {"functions": [], "issues": [], "parse_time_ms": 12.3}}
{"id": "550e8400-e29b-41d4-a716-446655440001", "error": {"message": "SyntaxError in input", "type": "ParseError"}}
```

### Python Backend Server (`kiro-carbon-optimizer/backend_server.py`)

The server reads lines from `sys.stdin`, dispatches by `method`, and writes responses to `sys.stdout`. It runs in a `while True` loop until stdin is closed (i.e., the extension process exits).

```python
DISPATCH = {
    "analyze_efficiency": lambda p: analyze_efficiency(p["code"]),
    "run_pipeline":       lambda p: run_pipeline(p["code"]),
    "analyze_configs":    lambda p: analyze_configs(p["workspace_root"]),
    "on_edit_generated":  lambda p: detector.on_edit_generated(p["file_path"], tuple(p["line_range"])),
}
```

Responses are serialized with `json.dumps(obj.to_dict())` for dataclass results, or `json.dumps({"error": {"message": ..., "type": ...}})` for `ErrorResponse` objects.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Bridge request/response round-trip

*For any* valid Bridge request (any method, any params, any UUID), serializing it to newline-delimited JSON and then deserializing the response should produce a result object that matches the original request's ID and contains either a `result` or an `error` field — never both, never neither.

**Validates: Requirements 1.4, 1.5**

---

### Property 2: Severity mapping is total and correct

*For any* `Issue` object with a `severity` field equal to `"HIGH"`, `"MEDIUM"`, or `"LOW"`, the `DiagnosticProvider` severity mapping function shall return `vscode.DiagnosticSeverity.Error`, `Warning`, or `Information` respectively — with no other possible output for these three inputs.

**Validates: Requirements 2.3, 2.4, 2.5**

---

### Property 3: Diagnostics reflect the latest analysis result

*For any* sequence of `AnalysisResult` objects published for the same file URI, the `DiagnosticCollection` shall contain exactly the diagnostics derived from the most recently published result — no more, no fewer.

**Validates: Requirements 2.6**

---

### Property 4: Closed file has no diagnostics

*For any* Python file that has been opened and analyzed (producing any number of diagnostics), closing that file shall result in the `DiagnosticCollection` containing zero entries for that file's URI.

**Validates: Requirements 2.7**

---

### Property 5: StruggleTracker fires at exactly the threshold

*For any* file and any sequence of save timestamps, the `StruggleTracker` shall return `true` from `recordSave` on the save that brings the count within the 10-minute sliding window to exactly 5, and shall return `false` for all saves before that point (within the same window after a reset).

**Validates: Requirements 6.2, 6.6**

---

### Property 6: StruggleTracker per-file isolation

*For any* two distinct file paths A and B, recording any number of saves on file A shall not change the `recentSaveCount` of file B.

**Validates: Requirements 6.7**

---

### Property 7: ReportPanel renders all error messages

*For any* error response from the backend (any `message` string, any `type` string), the `ReportPanel` shall render the error message string visibly in the WebView HTML output — it shall never silently swallow or omit the message.

**Validates: Requirements 4.5**

---

### Property 8: Bridge resolves every pending promise exactly once

*For any* set of concurrent `Bridge.call()` invocations, each call's returned promise shall be resolved or rejected exactly once — never zero times (dropped), never more than once (duplicated) — and the resolution value shall correspond to the response whose `id` matches the request's `id`.

**Validates: Requirements 1.8**

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Python executable not found | Show notification with setup instructions; do not spawn process |
| Backend process exits unexpectedly | Restart up to 3 times; after 3 failures show error notification and reject all pending promises |
| `analyze_efficiency` returns error | Log to Output channel; clear diagnostics for file; no user notification |
| `run_pipeline` returns error | Display error message in ReportPanel in place of report content |
| `analyze_configs` returns error | Log to Output channel; no notification |
| `on_edit_generated` returns error | Log to Output channel; no notification |
| Malformed JSON from backend stdout | Log parse error; reject the pending promise for that line if ID is recoverable |
| No active Python file when ReportPanel opened | Display "Open a Python file to run optimization." message |
| `pythonPath` setting changed | Terminate existing process; spawn new process with updated path; reset restart counter |

---

## Testing Strategy

### Unit Tests (Jest)

Unit tests cover pure logic and component behavior using manual VS Code API mocks.

**Bridge tests** (`src/__tests__/bridge.test.ts`):
- Verify request serialization produces valid newline-delimited JSON (Property 1)
- Verify response deserialization resolves the correct pending promise by ID (Property 8)
- Verify concurrent calls each resolve independently
- Verify restart logic: mock process exits 3 times, verify error notification shown
- Verify `dispose()` terminates the process and rejects all pending promises

**DiagnosticProvider tests** (`src/__tests__/diagnosticProvider.test.ts`):
- Verify severity mapping for HIGH/MEDIUM/LOW (Property 2)
- Verify diagnostics collection is replaced on each save (Property 3)
- Verify diagnostics are cleared on file close (Property 4)
- Verify `source` field is `"Carbon Optimizer"` on all diagnostics

**StruggleTracker tests** (`src/__tests__/struggleTracker.test.ts`):
- Verify warning fires at exactly the 5th save within 10 minutes (Property 5)
- Verify saves outside the 10-minute window do not count toward threshold
- Verify reset clears the history so subsequent saves start fresh (Property 5)
- Verify saves to file A do not affect file B's count (Property 6)

**ReportPanel tests** (`src/__tests__/reportPanel.test.ts`):
- Verify error message is rendered in HTML output for any error string (Property 7)
- Verify "Open a Python file" message shown when no active document
- Verify all required report sections are present in rendered HTML

### Property-Based Tests (fast-check)

Property-based tests use [fast-check](https://github.com/dubzzz/fast-check) with a minimum of 100 iterations per property.

Each test is tagged with a comment in the format:
`// Feature: carbon-optimizer-vscode-extension, Property N: <property_text>`

**Property 1 — Bridge round-trip** (`src/__tests__/bridge.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 1: Bridge request/response round-trip
fc.assert(fc.property(
  fc.record({ id: fc.uuid(), method: fc.string(), params: fc.object() }),
  (req) => { /* serialize, deserialize, verify id matches and result xor error present */ }
), { numRuns: 100 });
```

**Property 2 — Severity mapping** (`src/__tests__/diagnosticProvider.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 2: Severity mapping is total and correct
fc.assert(fc.property(
  fc.constantFrom('HIGH', 'MEDIUM', 'LOW'),
  (severity) => { /* verify mapSeverity(severity) returns correct DiagnosticSeverity */ }
), { numRuns: 100 });
```

**Property 3 — Diagnostics reflect latest result** (`src/__tests__/diagnosticProvider.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 3: Diagnostics reflect the latest analysis result
fc.assert(fc.property(
  fc.array(fc.array(arbitraryIssue(), { minLength: 0, maxLength: 10 }), { minLength: 1, maxLength: 5 }),
  (sequence) => { /* publish each result in sequence, verify collection matches last */ }
), { numRuns: 100 });
```

**Property 4 — Closed file has no diagnostics** (`src/__tests__/diagnosticProvider.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 4: Closed file has no diagnostics
fc.assert(fc.property(
  fc.array(arbitraryIssue(), { minLength: 1, maxLength: 20 }),
  (issues) => { /* set diagnostics, close file, verify collection is empty */ }
), { numRuns: 100 });
```

**Property 5 — StruggleTracker threshold** (`src/__tests__/struggleTracker.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 5: StruggleTracker fires at exactly the threshold
fc.assert(fc.property(
  fc.string(), // file path
  (filePath) => { /* record 4 saves, verify false; record 5th, verify true; reset; verify false */ }
), { numRuns: 100 });
```

**Property 6 — StruggleTracker isolation** (`src/__tests__/struggleTracker.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 6: StruggleTracker per-file isolation
fc.assert(fc.property(
  fc.string(), fc.string(), fc.integer({ min: 1, max: 10 }),
  (fileA, fileB, savesOnA) => {
    fc.pre(fileA !== fileB);
    /* record savesOnA saves on fileA, verify fileB count is 0 */
  }
), { numRuns: 100 });
```

**Property 7 — ReportPanel error rendering** (`src/__tests__/reportPanel.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 7: ReportPanel renders all error messages
fc.assert(fc.property(
  fc.string({ minLength: 1 }),
  (errorMessage) => { /* call renderError(errorMessage), verify output contains errorMessage */ }
), { numRuns: 100 });
```

**Property 8 — Bridge promise resolution** (`src/__tests__/bridge.property.test.ts`):
```
// Feature: carbon-optimizer-vscode-extension, Property 8: Bridge resolves every pending promise exactly once
fc.assert(fc.property(
  fc.array(fc.record({ method: fc.string(), params: fc.object() }), { minLength: 1, maxLength: 10 }),
  async (calls) => { /* fire all calls concurrently, verify each resolves exactly once with matching id */ }
), { numRuns: 100 });
```

### Integration Test

One integration test spawns the real Python backend and verifies a full round-trip:

```typescript
// src/__tests__/integration.test.ts
it('round-trips analyze_efficiency with real backend', async () => {
  const bridge = new Bridge('python3', path.resolve(__dirname, '../../kiro-carbon-optimizer/backend_server.py'));
  await bridge.start();
  const result = await bridge.call<AnalysisResult>('analyze_efficiency', { code: 'x = [i for i in range(1000)]' });
  expect(result).toHaveProperty('issues');
  bridge.dispose();
});
```

### VS Code API Mocking

The VS Code API is mocked using a manual `__mocks__/vscode.ts` module that stubs `DiagnosticCollection`, `window`, `workspace`, and `commands`. This avoids the overhead of `@vscode/test-electron` for unit tests while keeping integration tests runnable in CI.
