# Carbon-Aware Code Optimizer

A Kiro-native Python agent that analyzes Python source code for inefficiencies,
estimates its carbon footprint via sandboxed execution, generates optimized
versions, and produces a structured before-vs-after comparison report.

## Overview

The optimizer runs a five-step pipeline:

1. **Analyze** — parse code with `ast`, compute cyclomatic complexity via `radon`, detect nested loops and repeated sub-expressions.
2. **Measure (original)** — execute code in an isolated sandbox, capture wall-clock time, peak memory, energy (kWh), and CO₂ (grams) via CodeCarbon.
3. **Optimize** — apply rule-based AST transformation passes (loop reduction, expression hoisting, memoization, set-lookup substitution).
4. **Measure (optimized)** — repeat carbon measurement on the transformed code.
5. **Compare** — compute percentage improvements and generate a human-readable summary.

Two passive subsystems run alongside:
- **Struggle Detector** — monitors prompt patterns and edit history to surface AI retry-loop warnings.
- **Config Analyzer** — scans deployment configs (Dockerfile, GitHub Actions, Vercel, Netlify) for carbon-inefficient patterns.

## Project Structure

```
kiro-carbon-optimizer/
├── core/               # Analyzer, profiler, carbon estimator, optimizer, comparator, struggle detector, config analyzer
├── sandbox/            # Process-isolated code executor
├── tools/              # Kiro tool entry points (analyze, measure, optimize)
├── tests/
│   ├── unit/           # Unit tests for each component
│   ├── property/       # Hypothesis property-based tests
│   └── integration/    # End-to-end pipeline and sandbox isolation tests
├── kiro.yaml           # Tool declarations for the Kiro agent
└── requirements.txt    # Pinned Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

## Running Tests

```bash
pytest tests/
```

## Tools

| Tool | Input | Output |
|---|---|---|
| `analyze_efficiency` | `{code, language}` | `AnalysisResult` |
| `estimate_carbon` | `{code}` | `Metrics` |
| `optimize_code` | `{code, goal}` | `OptimizationResult` |
| `compare_versions` | `{original, optimized}` | `Comparison` |
