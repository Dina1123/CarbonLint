# Carbon Optimizer VS Code Extension

Analyzes Python code for carbon inefficiencies, estimates carbon footprint, and suggests optimizations directly in VS Code.

## Requirements

- VS Code 1.85.0 or later
- Python 3.11+ with the `kiro-carbon-optimizer` package installed

## Installation

Install from the `.vsix` file:
1. Open VS Code
2. Run `Extensions: Install from VSIX...` from the command palette
3. Select the `.vsix` file

## Configuration

| Setting | Default | Description |
|---|---|---|
| `carbonOptimizer.pythonPath` | `python3` | Path to the Python executable |

## Features

- **Analyze on save** — automatically analyzes Python files when saved
- **Inline diagnostics** — shows issues as squiggly underlines in the editor
- **Report panel** — full optimization report with before/after metrics
- **Config scan** — scans deployment configs on workspace open
- **Struggle detection** — warns when you may be in an AI retry loop

## Python Dependencies

```bash
pip install -r kiro-carbon-optimizer/requirements.txt
```
