# Requirements Document

## Introduction

The Carbon Optimizer VS Code Extension wraps the already-implemented `kiro-carbon-optimizer` Python backend and surfaces its analysis, optimization, and struggle-detection capabilities directly inside VS Code. The extension communicates with the Python backend via a spawned child process using JSON over stdin/stdout. It activates when a Python file is opened and provides five core features: automatic efficiency analysis on save with inline diagnostics, a sidebar WebView report panel for full optimization reports, deployment config scanning on workspace open, and AI retry-loop struggle detection based on save frequency.

## Glossary

- **Extension**: The VS Code extension (TypeScript) described in this document.
- **Backend**: The `kiro-carbon-optimizer` Python process spawned by the Extension.
- **Bridge**: The TypeScript module responsible for spawning the Backend process and serializing/deserializing JSON messages over stdin/stdout.
- **DiagnosticsProvider**: The Extension component that converts `AnalysisResult` issues into VS Code `Diagnostic` objects.
- **ReportPanel**: The VS Code WebView panel that displays full optimization reports and config scan results.
- **StruggleTracker**: The Extension-side component that tracks per-file save timestamps and triggers struggle warnings.
- **AnalysisResult**: The JSON object returned by the Backend's `analyze_efficiency` function, containing a list of `Issue` objects with `severity`, `line_number`, `description`, and `suggested_fix` fields.
- **Report**: The JSON object returned by the Backend's `run_pipeline` function, containing `analysis`, `original_metrics`, `optimized_code`, `optimized_metrics`, and `comparison` fields.
- **ConfigIssue**: The JSON object returned by the Backend's `analyze_configs` function, containing `file_path`, `line_number`, `description`, `carbon_impact_score`, and `remediation` fields.
- **StruggleSignal**: The JSON object returned by the Backend's struggle detection, containing `signal_type`, `severity`, and `message` fields.
- **Active File**: The Python file currently focused in the VS Code editor.
- **Workspace Root**: The top-level folder opened in VS Code, used as the root for config scanning.

---

## Requirements

### Requirement 1: Backend Process Management

**User Story:** As a developer, I want the extension to manage the Python backend process lifecycle, so that backend communication is reliable and transparent.

#### Acceptance Criteria

1. WHEN a Python file is opened in VS Code, THE Extension SHALL spawn the Backend as a child process using the Python executable path from extension settings.
2. WHEN the Backend process exits unexpectedly, THE Extension SHALL log the exit code and attempt to restart the Backend up to 3 times before surfacing an error notification.
3. IF the Python executable is not found at the configured path, THEN THE Extension SHALL display a notification with setup instructions and a link to configure the Python path setting.
4. THE Bridge SHALL serialize all requests to the Backend as newline-delimited JSON objects written to the Backend's stdin.
5. THE Bridge SHALL deserialize all responses from the Backend as newline-delimited JSON objects read from the Backend's stdout.
6. THE Extension SHALL expose a configuration setting `carbonOptimizer.pythonPath` that defaults to `python3` and accepts an absolute path to a Python executable.
7. WHEN the `carbonOptimizer.pythonPath` setting is changed, THE Extension SHALL terminate the existing Backend process and spawn a new one using the updated path.
8. THE Bridge SHALL process all Backend calls asynchronously so that THE Extension does not block the VS Code UI thread.

---

### Requirement 2: Analyze on Save

**User Story:** As a developer, I want my Python files to be automatically analyzed for inefficiencies when I save them, so that I get immediate feedback without manual action.

#### Acceptance Criteria

1. WHEN a Python file is saved in VS Code, THE Extension SHALL send the file's full text content to the Backend's `analyze_efficiency` function via the Bridge.
2. WHEN the Backend returns an `AnalysisResult`, THE DiagnosticsProvider SHALL convert each `Issue` in the result into a VS Code `Diagnostic` object targeting the reported `line_number`.
3. WHEN an `Issue` has `severity` equal to `"HIGH"`, THE DiagnosticsProvider SHALL assign the `Diagnostic` a severity of `Error`.
4. WHEN an `Issue` has `severity` equal to `"MEDIUM"`, THE DiagnosticsProvider SHALL assign the `Diagnostic` a severity of `Warning`.
5. WHEN an `Issue` has `severity` equal to `"LOW"`, THE DiagnosticsProvider SHALL assign the `Diagnostic` a severity of `Information`.
6. THE DiagnosticsProvider SHALL publish all diagnostics to the VS Code `DiagnosticCollection` for the saved file, replacing any previously published diagnostics for that file.
7. WHEN a Python file is closed, THE DiagnosticsProvider SHALL clear all diagnostics associated with that file.
8. WHEN the Backend returns an error response for an `analyze_efficiency` call, THE Extension SHALL log the error message and clear any existing diagnostics for the file without displaying a user-facing error notification.
9. WHILE the Backend is processing an `analyze_efficiency` request, THE Extension SHALL display a status bar item with the text "Carbon: Analyzing…".
10. WHEN the analysis completes, THE Extension SHALL update the status bar item to show the count of issues found (e.g., "Carbon: 3 issues").
11. THE Extension SHALL complete the analysis and update diagnostics within 3 seconds for Python files containing fewer than 500 lines.

---

### Requirement 3: Inline Issue Highlighting and Hover Tooltips

**User Story:** As a developer, I want to see exactly which lines have issues and read fix suggestions on hover, so that I can understand and address problems in context.

#### Acceptance Criteria

1. THE DiagnosticsProvider SHALL underline the full text of the line identified by `line_number` in each `Issue` using VS Code's diagnostic decoration mechanism.
2. WHEN a developer hovers over an underlined line, THE Extension SHALL display a hover tooltip containing the `Issue`'s `description` and `suggested_fix` fields.
3. THE Extension SHALL register a `HoverProvider` for the `python` language that retrieves the `Issue` matching the hovered line from the active `DiagnosticCollection`.
4. THE Extension SHALL display all published diagnostics in the VS Code Problems panel under the source label `"Carbon Optimizer"`.
5. WHEN no issues are found for a file, THE DiagnosticsProvider SHALL clear all diagnostics for that file so that the Problems panel shows zero entries for it.

---

### Requirement 4: Sidebar Report Panel

**User Story:** As a developer, I want a sidebar panel that shows the full optimization report for my active file, so that I can review before/after metrics and apply optimizations.

#### Acceptance Criteria

1. THE Extension SHALL register a VS Code command `carbonOptimizer.openReport` that opens the ReportPanel as a WebView panel in the VS Code sidebar or editor area.
2. WHEN the `carbonOptimizer.openReport` command is executed, THE ReportPanel SHALL display a loading indicator while the Backend processes the request.
3. WHEN the ReportPanel is open and the developer clicks the "Optimize" button, THE Extension SHALL send the Active File's full text to the Backend's `run_pipeline` function via the Bridge.
4. WHEN the Backend returns a `Report`, THE ReportPanel SHALL display the following sections:
   a. Original metrics: `execution_time_ms`, `memory_used_bytes`, `energy_kwh`, `co2_grams`
   b. A diff view showing the original code versus `optimized_code`
   c. Optimized metrics: `execution_time_ms`, `memory_used_bytes`, `energy_kwh`, `co2_grams`
   d. Comparison percentages: `execution_time_improvement_pct`, `memory_improvement_pct`, `co2_improvement_pct`, and `summary`
5. IF the Backend returns an error response for a `run_pipeline` call, THEN THE ReportPanel SHALL display the error message in place of the report content.
6. THE Extension SHALL register the ReportPanel as accessible from the VS Code command palette via the `carbonOptimizer.openReport` command.
7. WHEN the ReportPanel is opened and no Python file is active in the editor, THE ReportPanel SHALL display the message "Open a Python file to run optimization."
8. THE ReportPanel SHALL remain open and retain its last displayed report when the developer switches to a different file.

---

### Requirement 5: Config Scan on Workspace Open

**User Story:** As a developer, I want my deployment configuration files to be automatically scanned when I open a workspace, so that I am alerted to carbon-inefficient settings without manual action.

#### Acceptance Criteria

1. WHEN a VS Code workspace is opened, THE Extension SHALL send the Workspace Root path to the Backend's `analyze_configs` function via the Bridge.
2. WHEN the Backend returns a non-empty list of `ConfigIssue` objects, THE Extension SHALL display a VS Code information notification with the message: "Carbon Optimizer: [N] deployment config issue(s) found. Click to view."
3. WHEN the developer clicks the notification action, THE Extension SHALL open the ReportPanel and display the list of `ConfigIssue` objects, showing each issue's `file_path`, `line_number`, `description`, `carbon_impact_score`, and `remediation`.
4. WHEN the Backend returns an empty list of `ConfigIssue` objects, THE Extension SHALL not display any notification.
5. IF the Backend returns an error response for an `analyze_configs` call, THEN THE Extension SHALL log the error and not display a notification to the developer.
6. THE Extension SHALL perform the config scan asynchronously so that workspace startup is not delayed.

---

### Requirement 6: Struggle Detection

**User Story:** As a developer, I want to be warned when I appear to be in an AI retry loop based on my save frequency, so that I can break the loop and add better context.

#### Acceptance Criteria

1. THE StruggleTracker SHALL record a timestamp for each save event on every Python file opened in the Extension.
2. WHEN a Python file has been saved 5 or more times within a 10-minute sliding window, THE StruggleTracker SHALL trigger a struggle warning for that file.
3. WHEN a struggle warning is triggered, THE Extension SHALL display a VS Code warning notification with the message: "Carbon Optimizer: You've saved [filename] 5 times in 10 minutes. You may be in an AI retry loop. Consider adding more context."
4. WHEN a struggle warning is triggered, THE Extension SHALL call the Backend's `on_edit_generated` signal via the Bridge with the file path and the full line range of the file.
5. WHEN the Backend returns one or more `StruggleSignal` objects from `on_edit_generated`, THE Extension SHALL append each signal's `message` to the VS Code Output channel named "Carbon Optimizer".
6. THE StruggleTracker SHALL reset the save count for a file after a struggle warning has been displayed, so that subsequent saves start a new 10-minute window.
7. THE StruggleTracker SHALL maintain independent save histories for each open file so that saves to one file do not affect the warning threshold of another file.

---

### Requirement 7: Cross-Platform Compatibility and Packaging

**User Story:** As a developer on any operating system, I want the extension to work reliably and be installable as a .vsix file, so that I can use it regardless of my platform.

#### Acceptance Criteria

1. THE Extension SHALL spawn the Backend process using platform-appropriate path separators and shell conventions on Windows, macOS, and Linux.
2. THE Extension SHALL be packaged as a `.vsix` file using the `vsce` tool, including all compiled TypeScript output and static WebView assets.
3. THE Extension SHALL declare activation events in `package.json` so that THE Extension activates when a file with the language identifier `python` is opened.
4. THE Extension SHALL specify a minimum VS Code engine version of `1.85.0` in `package.json`.
5. WHEN the Backend process is spawned on Windows, THE Extension SHALL use `python` as the default executable name if `python3` is not found, falling back gracefully.
6. THE Extension SHALL include a `README.md` describing installation steps, the `carbonOptimizer.pythonPath` setting, and required Python dependencies.
