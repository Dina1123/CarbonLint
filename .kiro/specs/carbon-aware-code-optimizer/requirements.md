# Requirements Document

## Introduction

The Carbon-Aware Code Optimization Extension is a Kiro-native agent that analyzes Python source code for inefficiencies, estimates its carbon footprint via resource usage measurement, generates optimized versions, and produces a structured before-vs-after comparison report. The system does not directly measure carbon emissions from infrastructure; instead it maps code efficiency metrics (execution time, memory usage, energy consumption) to CO₂ estimates using the CodeCarbon library.

The agent exposes four tools — `analyze_efficiency`, `estimate_carbon`, `optimize_code`, and `compare_versions` — and orchestrates them in a fixed pipeline when a user requests code optimization.

## Glossary

- **Agent**: The Kiro-native orchestration layer that sequences tool calls and returns the final report to the user.
- **Analyzer**: The component that parses Python source code using AST and computes complexity metrics.
- **Carbon_Estimator**: The component that executes code in a sandboxed environment, measures resource usage, and maps measurements to CO₂ estimates using CodeCarbon.
- **Optimizer**: The component that applies rule-based transformations to source code to reduce energy consumption while preserving original functionality.
- **Comparator**: The component that computes percentage improvements between original and optimized metric sets.
- **Sandbox**: The isolated execution environment used by the Carbon_Estimator to run untrusted code safely.
- **Complexity_Score**: A numeric value produced by radon representing the cyclomatic complexity of a Python function or module.
- **Issue**: A structured object describing a detected inefficiency, including a description and a suggested fix.
- **Metrics**: A structured object containing `execution_time_ms`, `memory_used_bytes`, `energy_kwh`, and `co2_grams` for a given code sample.
- **Report**: The final structured JSON output returned by the Agent containing analysis, original metrics, optimized code, optimized metrics, and comparison.

---

## Requirements

### Requirement 1: Python Code Efficiency Analysis

**User Story:** As a developer, I want the agent to analyze my Python code for inefficiencies, so that I understand which patterns are causing high resource usage before any optimization is applied.

#### Acceptance Criteria

1. WHEN `analyze_efficiency` is called with a valid Python code string, THE Analyzer SHALL parse the code using Python's AST module and return a structured result within 2 seconds.
2. THE Analyzer SHALL compute a Complexity_Score for each function in the provided code using radon cyclomatic complexity.
3. WHEN the code contains nested loops of depth 2 or greater, THE Analyzer SHALL include an Issue identifying the location (line number) and a suggested refactoring approach.
4. WHEN the code contains repeated identical sub-expressions evaluated inside a loop body, THE Analyzer SHALL include an Issue recommending caching or hoisting the expression.
5. IF the provided code string is empty or contains a syntax error, THEN THE Analyzer SHALL return a structured error response with a descriptive message and no partial results.
6. THE Analyzer SHALL return issues as an ordered list sorted by severity (highest Complexity_Score first).

---

### Requirement 2: Carbon Footprint Estimation

**User Story:** As a developer, I want the agent to estimate the carbon footprint of my code, so that I can understand its environmental impact in concrete terms.

#### Acceptance Criteria

1. WHEN `estimate_carbon` is called with a valid Python code string, THE Carbon_Estimator SHALL execute the code inside the Sandbox and return Metrics within 5 seconds.
2. THE Carbon_Estimator SHALL measure wall-clock execution time in milliseconds and include it in the returned Metrics as `execution_time_ms`.
3. THE Carbon_Estimator SHALL measure peak memory consumption in bytes and include it in the returned Metrics as `memory_used_bytes`.
4. THE Carbon_Estimator SHALL use CodeCarbon to derive `energy_kwh` and `co2_grams` from the measured execution and include both values in the returned Metrics.
5. IF the code execution inside the Sandbox raises an unhandled exception, THEN THE Carbon_Estimator SHALL return a structured error response containing the exception type and message, and SHALL NOT return partial Metrics.
6. IF the code execution inside the Sandbox exceeds 5 seconds, THEN THE Carbon_Estimator SHALL terminate the execution and return a timeout error response.
7. THE Carbon_Estimator SHALL produce deterministic Metrics for the same input code across repeated calls on the same hardware (variance in `execution_time_ms` SHALL be within ±10% across 3 consecutive runs under idle system conditions).

---

### Requirement 3: Sandboxed Code Execution

**User Story:** As a platform operator, I want all user-submitted code to run in an isolated environment, so that malicious or buggy code cannot affect the host system.

#### Acceptance Criteria

1. THE Sandbox SHALL execute code in a process-isolated environment that prevents access to the host filesystem outside a designated temporary directory.
2. THE Sandbox SHALL restrict network access during code execution.
3. WHEN code execution completes or is terminated, THE Sandbox SHALL release all allocated resources and remove any temporary files created during execution.
4. IF executed code attempts to import a module outside an approved allowlist, THEN THE Sandbox SHALL raise an `ImportError` and terminate execution.
5. THE Sandbox SHALL enforce a configurable memory limit; IF executed code exceeds this limit, THEN THE Sandbox SHALL terminate execution and return a memory-exceeded error response.

---

### Requirement 4: Rule-Based Code Optimization

**User Story:** As a developer, I want the agent to generate an optimized version of my code, so that I can adopt energy-efficient patterns without manually rewriting everything.

#### Acceptance Criteria

1. WHEN `optimize_code` is called with a valid Python code string and goal `"reduce_energy"`, THE Optimizer SHALL return an optimized code string, a list of applied changes, and an `expected_improvement_percent` value.
2. THE Optimizer SHALL apply loop-reduction transformations when nested loops of depth 2 or greater are detected.
3. THE Optimizer SHALL apply memoization or result-caching transformations when repeated identical sub-expressions inside loop bodies are detected.
4. THE Optimizer SHALL apply algorithmic substitutions (e.g., replacing O(n²) list searches with O(1) set lookups) when the pattern is unambiguously detectable via AST analysis.
5. THE Optimizer SHALL preserve the observable behavior of the original code; the optimized code SHALL produce identical outputs for all valid inputs that the original code accepts.
6. IF no optimizable patterns are detected, THEN THE Optimizer SHALL return the original code unchanged, an empty changes list, and `expected_improvement_percent` of 0.
7. THE Optimizer SHALL include a human-readable description for each applied change in the changes list.

---

### Requirement 5: Before-vs-After Comparison

**User Story:** As a developer, I want a clear comparison between the original and optimized code metrics, so that I can quantify the environmental benefit of the optimization.

#### Acceptance Criteria

1. WHEN `compare_versions` is called with original Metrics and optimized Metrics, THE Comparator SHALL return percentage improvements for `execution_time_ms`, `memory_used_bytes`, and `co2_grams`.
2. THE Comparator SHALL compute improvement percentage as `((original - optimized) / original) * 100`, rounded to two decimal places.
3. WHEN the optimized value for a metric is greater than the original value, THE Comparator SHALL report a negative improvement percentage for that metric.
4. THE Comparator SHALL include a human-readable `summary` string that states the overall carbon reduction in grams and percentage.
5. IF either the original or optimized Metrics object is missing a required field, THEN THE Comparator SHALL return a structured error response identifying the missing field.

---

### Requirement 6: Agent Orchestration Pipeline

**User Story:** As a developer, I want to say "Optimize this code" and receive a complete analysis and optimization report, so that I don't have to manually invoke each tool in sequence.

#### Acceptance Criteria

1. WHEN the Agent receives a user request containing Python code and an optimization intent, THE Agent SHALL invoke `analyze_efficiency`, then `estimate_carbon` on the original code, then `optimize_code`, then `estimate_carbon` on the optimized code, then `compare_versions`, in that order.
2. THE Agent SHALL return a single structured Report containing: `analysis` (output of `analyze_efficiency`), `original_metrics` (first `estimate_carbon` output), `optimized_code` (from `optimize_code`), `optimized_metrics` (second `estimate_carbon` output), and `comparison` (output of `compare_versions`).
3. IF any tool in the pipeline returns an error response, THEN THE Agent SHALL halt the pipeline and return a structured error Report identifying which tool failed and including the tool's error message.
4. THE Agent SHALL NOT modify the user's code between pipeline steps; the code passed to `optimize_code` SHALL be identical to the code passed to the first `estimate_carbon` call.

---

### Requirement 7: AST Round-Trip Integrity

**User Story:** As a developer, I want the optimizer to only produce syntactically valid Python code, so that I can safely use the output without manual correction.

#### Acceptance Criteria

1. THE Optimizer SHALL parse the optimized code string back through Python's AST module after applying transformations; IF the re-parse fails, THEN THE Optimizer SHALL discard the transformation and return the original code for that transformation step.
2. FOR ALL valid Python code inputs, applying `optimize_code` then parsing the returned optimized code string SHALL produce a valid AST (round-trip parse property).
3. THE Optimizer SHALL not alter string literals, numeric literals, or comments in the original code unless the alteration is a direct consequence of an applied optimization transformation.

---

### Requirement 8: Structured and Explainable Output

**User Story:** As a developer, I want all outputs to follow a consistent, documented JSON schema, so that I can integrate the agent's results into other tools or workflows.

#### Acceptance Criteria

1. THE Agent SHALL return all outputs as valid JSON objects conforming to the documented Report schema.
2. THE Analyzer SHALL return all outputs as valid JSON objects conforming to the documented analysis schema.
3. THE Carbon_Estimator SHALL return all outputs as valid JSON objects conforming to the documented Metrics schema.
4. THE Optimizer SHALL return all outputs as valid JSON objects conforming to the documented optimization schema.
5. THE Comparator SHALL return all outputs as valid JSON objects conforming to the documented comparison schema.
6. WHEN a tool returns an error response, THE tool SHALL include at minimum the fields `"error": true`, `"tool": "<tool_name>"`, and `"message": "<description>"` in the JSON response.
