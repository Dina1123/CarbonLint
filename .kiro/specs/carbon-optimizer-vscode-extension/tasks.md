# Implementation Plan: Carbon Optimizer VS Code Extension

## Overview

Implement the Carbon Optimizer VS Code Extension in TypeScript, communicating with the existing `kiro-carbon-optimizer` Python backend via a spawned subprocess using newline-delimited JSON over stdin/stdout. The implementation follows the component order: Python backend server → extension scaffolding → VS Code API mock → Bridge → DiagnosticProvider → StruggleTracker → ReportPanel → ConfigScanner → extension.ts wiring → tests → packaging.

## Tasks

- [x] 1. Create Python backend server
  - Create `kiro-carbon-optimizer/backend_server.py` with a `while True` stdin read loop
  - Implement the `DISPATCH` table mapping method names to core tool functions: `analyze_efficiency`, `run_pipeline`, `analyze_configs`, `on_edit_generated`
  - Serialize successful results with `json.dumps(result.to_dict())` and write to stdout followed by `\n`
  - Serialize error responses as `{"id": ..., "error": {"message": ..., "type": ...}}` for any exception
  - Flush stdout after every write so the extension receives responses immediately
  - _Requirements: 1.4, 1.5_

- [x] 2. Scaffold extension project structure
  - [x] 2.1 Create `carbon-optimizer-extension/package.json`
    - Set `"engines": {"vscode": "^1.85.0"}`, `"activationEvents": ["onLanguage:python"]`
    - Declare command `carbonOptimizer.openReport` in `contributes.commands`
    - Declare configuration `carbonOptimizer.pythonPath` with default `"python3"`
    - Add `devDependencies`: `typescript`, `@types/vscode`, `@types/node`, `jest`, `ts-jest`, `@types/jest`, `fast-check`, `vsce`
    - Add `dependencies`: `uuid`, `@types/uuid`
    - Add `scripts`: `compile`, `test`, `package`
    - _Requirements: 7.3, 7.4, 1.6_
  - [x] 2.2 Create `carbon-optimizer-extension/tsconfig.json`
    - Target `ES2020`, module `commonjs`, `outDir: "out"`, `strict: true`
    - Include `src/**/*` and `__mocks__/**/*`
    - _Requirements: 7.1_

- [x] 3. Create VS Code API mock
  - Create `carbon-optimizer-extension/__mocks__/vscode.ts`
  - Stub `DiagnosticCollection` with `set`, `delete`, `clear`, `get` methods backed by a `Map`
  - Stub `window.showInformationMessage`, `showWarningMessage`, `showErrorMessage`, `createStatusBarItem`, `createOutputChannel`, `createWebviewPanel`
  - Stub `workspace.onDidSaveTextDocument`, `onDidCloseTextDocument`, `onDidChangeWorkspaceFolders`, `workspaceFolders`
  - Stub `languages.createDiagnosticCollection`, `registerHoverProvider`
  - Stub `commands.registerCommand`
  - Export `DiagnosticSeverity` enum with values `Error=0`, `Warning=1`, `Information=2`
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [x] 4. Implement Bridge
  - [x] 4.1 Create `carbon-optimizer-extension/src/bridge.ts`
    - Define `BridgeRequest`, `BridgeResponse`, and `BridgeError` interfaces matching the design protocol
    - Implement `Bridge` class with `private process`, `private pending: Map<string, {resolve, reject}>`, `private restartCount`, `readonly MAX_RESTARTS = 3`
    - Implement `start()`: spawn child process with `pythonPath` and `serverScriptPath`, attach stdout line reader, attach `close` handler for restart logic
    - Implement `call<T>(method, params)`: generate UUID v4, store promise callbacks in `pending`, write newline-delimited JSON to stdin, return promise
    - Implement stdout reader: split on `\n`, parse JSON, look up ID in `pending`, resolve or reject
    - Implement restart logic: on `close` event, if `restartCount < MAX_RESTARTS` increment and call `start()`; after 3 failures reject all pending and show VS Code error notification; reset `restartCount` to 0 on first successful response
    - Implement `dispose()`: terminate process and reject all pending promises
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.8_
  - [ ]* 4.2 Write unit tests for Bridge
    - Test request serialization produces valid newline-delimited JSON
    - Test response deserialization resolves the correct pending promise by ID
    - Test concurrent calls each resolve independently
    - Test restart logic: mock process exits 3 times, verify error notification shown
    - Test `dispose()` terminates process and rejects all pending promises
    - _Requirements: 1.2, 1.4, 1.5, 1.8_
  - [ ]* 4.3 Write property test for Bridge round-trip (Property 1)
    - `// Feature: carbon-optimizer-vscode-extension, Property 1: Bridge request/response round-trip`
    - Use `fc.record({ id: fc.uuid(), method: fc.string(), params: fc.object() })` to generate requests
    - Verify serialized+deserialized response has matching ID and exactly one of `result` or `error`
    - Minimum 100 runs
    - _Requirements: 1.4, 1.5_
  - [ ]* 4.4 Write property test for Bridge promise resolution (Property 8)
    - `// Feature: carbon-optimizer-vscode-extension, Property 8: Bridge resolves every pending promise exactly once`
    - Use `fc.array(fc.record({ method: fc.string(), params: fc.object() }), { minLength: 1, maxLength: 10 })`
    - Fire all calls concurrently, verify each resolves exactly once with matching ID
    - Minimum 100 runs
    - _Requirements: 1.8_

- [x] 5. Implement DiagnosticProvider
  - [x] 5.1 Create `carbon-optimizer-extension/src/diagnosticProvider.ts`
    - Implement `DiagnosticProvider` class with `private collection: vscode.DiagnosticCollection` and `private bridge: Bridge`
    - Implement `register(context)`: subscribe to `onDidSaveTextDocument` (Python files only) and `onDidCloseTextDocument`
    - Implement `onSave(document)`: show "Carbon: Analyzing…" status bar item, call `bridge.call('analyze_efficiency', {code})`, convert issues to diagnostics, update status bar to "Carbon: N issues", publish to collection
    - Implement `onClose(document)`: call `collection.delete(document.uri)`
    - Implement `toDiagnostics(issues, document)`: map each issue to a `vscode.Diagnostic` with full-line range at `line_number - 1`, correct severity, `source: "Carbon Optimizer"`, `message: issue.description`, `code: issue.suggested_fix`
    - Implement severity mapping: `"HIGH"` → `Error`, `"MEDIUM"` → `Warning`, `"LOW"` → `Information`
    - On backend error: log to Output channel, clear diagnostics for file, no user notification
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 3.1, 3.4, 3.5_
  - [ ]* 5.2 Write unit tests for DiagnosticProvider
    - Test severity mapping for HIGH/MEDIUM/LOW
    - Test diagnostics collection is replaced on each save
    - Test diagnostics are cleared on file close
    - Test `source` field is `"Carbon Optimizer"` on all diagnostics
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7_
  - [ ]* 5.3 Write property test for severity mapping (Property 2)
    - `// Feature: carbon-optimizer-vscode-extension, Property 2: Severity mapping is total and correct`
    - Use `fc.constantFrom('HIGH', 'MEDIUM', 'LOW')` to generate severity values
    - Verify `mapSeverity(severity)` returns the correct `DiagnosticSeverity` for each input
    - Minimum 100 runs
    - _Requirements: 2.3, 2.4, 2.5_
  - [ ]* 5.4 Write property test for diagnostics reflecting latest result (Property 3)
    - `// Feature: carbon-optimizer-vscode-extension, Property 3: Diagnostics reflect the latest analysis result`
    - Use `fc.array(fc.array(arbitraryIssue(), { minLength: 0, maxLength: 10 }), { minLength: 1, maxLength: 5 })`
    - Publish each result in sequence for the same URI, verify collection matches only the last result
    - Minimum 100 runs
    - _Requirements: 2.6_
  - [ ]* 5.5 Write property test for closed file has no diagnostics (Property 4)
    - `// Feature: carbon-optimizer-vscode-extension, Property 4: Closed file has no diagnostics`
    - Use `fc.array(arbitraryIssue(), { minLength: 1, maxLength: 20 })`
    - Set diagnostics for a URI, trigger close, verify collection is empty for that URI
    - Minimum 100 runs
    - _Requirements: 2.7_

- [x] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement StruggleTracker
  - [x] 7.1 Create `carbon-optimizer-extension/src/struggleTracker.ts`
    - Implement `StruggleTracker` class with `private saveHistory: Map<string, number[]>`, `readonly WINDOW_MS = 600000`, `readonly THRESHOLD = 5`
    - Implement `recordSave(filePath)`: append `Date.now()`, prune entries older than `WINDOW_MS`, return `true` if count reaches `THRESHOLD`
    - Implement `reset(filePath)`: clear the save history array for the given file path
    - Implement `recentSaveCount(filePath, nowMs?)`: return count of timestamps within `WINDOW_MS` of `nowMs ?? Date.now()`
    - _Requirements: 6.1, 6.2, 6.6, 6.7_
  - [ ]* 7.2 Write unit tests for StruggleTracker
    - Test warning fires at exactly the 5th save within 10 minutes
    - Test saves outside the 10-minute window do not count toward threshold
    - Test reset clears history so subsequent saves start fresh
    - Test saves to file A do not affect file B's count
    - _Requirements: 6.2, 6.6, 6.7_
  - [ ]* 7.3 Write property test for StruggleTracker threshold (Property 5)
    - `// Feature: carbon-optimizer-vscode-extension, Property 5: StruggleTracker fires at exactly the threshold`
    - Use `fc.string()` for file path
    - Record 4 saves, verify `false`; record 5th, verify `true`; call `reset`, verify subsequent saves return `false` until threshold again
    - Minimum 100 runs
    - _Requirements: 6.2, 6.6_
  - [ ]* 7.4 Write property test for StruggleTracker per-file isolation (Property 6)
    - `// Feature: carbon-optimizer-vscode-extension, Property 6: StruggleTracker per-file isolation`
    - Use `fc.string()`, `fc.string()`, `fc.integer({ min: 1, max: 10 })` for fileA, fileB, savesOnA
    - Apply `fc.pre(fileA !== fileB)`; record savesOnA saves on fileA, verify `recentSaveCount(fileB)` is 0
    - Minimum 100 runs
    - _Requirements: 6.7_

- [x] 8. Implement ReportPanel
  - [x] 8.1 Create `carbon-optimizer-extension/media/report.html`
    - Define HTML template with placeholders for report sections: original metrics, code diff, optimized metrics, comparison percentages
    - Include loading indicator element and error message container
    - Use `acquireVsCodeApi()` for message passing between WebView and extension
    - _Requirements: 4.2, 4.4, 4.5, 4.7_
  - [x] 8.2 Create `carbon-optimizer-extension/src/reportPanel.ts`
    - Implement `ReportPanel` class with `private panel: vscode.WebviewPanel | undefined` and `private bridge: Bridge`
    - Implement `show(activeDocument?)`: create or reveal panel; if no active Python document render "Open a Python file to run optimization." message; otherwise show loading indicator and wire "Optimize" button handler
    - Implement `renderReport(report)`: build HTML string with all required sections (original metrics, diff view, optimized metrics, comparison percentages and summary)
    - Implement `renderConfigIssues(issues)`: build HTML string listing each `ConfigIssue` with `file_path`, `line_number`, `description`, `carbon_impact_score`, `remediation`
    - Implement `renderError(message)`: build HTML string that visibly displays the error message
    - On "Optimize" button click: call `bridge.call('run_pipeline', {code})`, render report or render error on failure
    - Panel retains last content when user switches files (no auto-refresh)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.3_
  - [ ]* 8.3 Write unit tests for ReportPanel
    - Test error message is rendered in HTML output for any error string
    - Test "Open a Python file" message shown when no active document
    - Test all required report sections are present in rendered HTML
    - Test `renderConfigIssues` includes all required ConfigIssue fields
    - _Requirements: 4.4, 4.5, 4.7_
  - [ ]* 8.4 Write property test for ReportPanel error rendering (Property 7)
    - `// Feature: carbon-optimizer-vscode-extension, Property 7: ReportPanel renders all error messages`
    - Use `fc.string({ minLength: 1 })` to generate arbitrary error messages
    - Call `renderError(errorMessage)`, verify the output HTML string contains the exact `errorMessage`
    - Minimum 100 runs
    - _Requirements: 4.5_

- [x] 9. Implement ConfigScanner
  - Create `carbon-optimizer-extension/src/configScanner.ts`
  - Implement `ConfigScanner` class with `private bridge: Bridge` and `private hasScanned: Set<string>`
  - Implement `register(context)`: scan all currently open workspace folders on activation; subscribe to `onDidChangeWorkspaceFolders` for newly added folders
  - Implement `scan(workspaceRoot)`: skip if already in `hasScanned`; add to `hasScanned`; call `bridge.call('analyze_configs', {workspace_root})`; on non-empty result show information notification "Carbon Optimizer: [N] deployment config issue(s) found. Click to view." with action to open ReportPanel; on empty result do nothing; on error log to Output channel
  - Run scan asynchronously so workspace startup is not delayed
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 10. Implement extension.ts and wire all components
  - Create `carbon-optimizer-extension/src/extension.ts`
  - Implement `activate(context)`: read `carbonOptimizer.pythonPath` setting, resolve `backend_server.py` path, instantiate `Bridge`, `DiagnosticProvider`, `StruggleTracker`, `ReportPanel`, `ConfigScanner`
  - Call `bridge.start()`, `diagnosticProvider.register(context)`, `configScanner.register(context)`
  - Register command `carbonOptimizer.openReport` that calls `reportPanel.show(activeEditor?.document)`
  - Register `HoverProvider` for `python` language that retrieves the matching issue from the active `DiagnosticCollection` and returns a hover with `description` and `suggested_fix`
  - Subscribe to `onDidSaveTextDocument`: call `struggleTracker.recordSave(filePath)`; if `true`, show warning notification, call `bridge.call('on_edit_generated', {file_path, line_range})`, append each `StruggleSignal.message` to Output channel, call `struggleTracker.reset(filePath)`
  - Subscribe to `onDidChangeConfiguration`: if `carbonOptimizer.pythonPath` changed, dispose bridge and create new one with updated path
  - Implement `deactivate()`: call `bridge.dispose()`
  - Push all disposables to `context.subscriptions`
  - _Requirements: 1.1, 1.3, 1.6, 1.7, 2.1, 3.2, 3.3, 4.1, 4.6, 6.3, 6.4, 6.5, 7.1, 7.3_

- [x] 11. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Write integration test
  - Create `carbon-optimizer-extension/src/__tests__/integration.test.ts`
  - Spawn the real Python backend via `Bridge` using `python3` and the resolved path to `kiro-carbon-optimizer/backend_server.py`
  - Call `bridge.call('analyze_efficiency', { code: 'x = [i for i in range(1000)]' })` and verify the result has an `issues` property
  - Call `bridge.dispose()` in `afterAll` to clean up the process
  - _Requirements: 1.4, 1.5, 2.1_

- [x] 13. Package extension as .vsix
  - Add `vsce` to `devDependencies` and add a `"package": "vsce package"` script in `package.json`
  - Create `carbon-optimizer-extension/README.md` describing installation steps, the `carbonOptimizer.pythonPath` setting, and required Python dependencies
  - Create `.vscodeignore` to exclude `src`, `node_modules`, test files, and `__mocks__` from the package
  - Run `npm run compile` then `vsce package` to produce the `.vsix` artifact
  - _Requirements: 7.2, 7.6_

- [x] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate the 8 correctness properties defined in the design document
- Unit tests validate specific examples and edge cases
- The VS Code API mock in `__mocks__/vscode.ts` enables unit tests to run without `@vscode/test-electron`
- The integration test requires a working Python 3 environment with `kiro-carbon-optimizer` dependencies installed
