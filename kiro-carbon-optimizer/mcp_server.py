"""MCP server exposing the Carbon-Aware Code Optimizer tools to Kiro."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from tools.optimize import run_pipeline, optimize_code, compare_versions
from tools.analyze import analyze_efficiency
from tools.measure import estimate_carbon
from core.config_analyzer import analyze_configs
from core.struggle_detector import StruggleDetector

mcp = FastMCP("carbon-optimizer")
_struggle_detector = StruggleDetector()


@mcp.tool()
def optimize_python_code(code: str) -> str:
    """
    Run the full carbon-aware optimization pipeline on Python code.
    Analyzes inefficiencies, estimates carbon footprint, optimizes the code,
    and returns a structured before/after comparison report.
    """
    result = run_pipeline(code)
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def analyze_python_code(code: str) -> str:
    """
    Analyze Python code for inefficiencies (nested loops, repeated expressions).
    Returns complexity scores and a list of issues sorted by severity.
    """
    result = analyze_efficiency(code)
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def measure_carbon_footprint(code: str) -> str:
    """
    Execute Python code in a sandbox and estimate its carbon footprint.
    Returns execution time, memory usage, energy (kWh), and CO2 (grams).
    """
    result = estimate_carbon(code)
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def scan_deployment_configs(workspace_path: str) -> str:
    """
    Scan a workspace directory for carbon-inefficient deployment configurations.
    Checks Dockerfile, .dockerignore, vercel.json, netlify.toml, and GitHub Actions workflows.
    Returns issues sorted by carbon impact (HIGH > MEDIUM > LOW).
    """
    issues = analyze_configs(workspace_path)
    return json.dumps([i.to_dict() for i in issues], indent=2)


@mcp.tool()
def report_prompt(prompt: str, file_refs: str = "") -> str:
    """
    Report a submitted AI prompt to the struggle detector.
    Detects retry loops, oversized prompts, and high-frequency file requests.
    Returns any triggered struggle signals with MCP server suggestions.
    file_refs: comma-separated list of file paths referenced in the prompt.
    """
    refs = [f.strip() for f in file_refs.split(",") if f.strip()]
    signals = _struggle_detector.on_prompt_submitted(prompt, refs)
    return json.dumps([s.to_dict() for s in signals], indent=2)


if __name__ == "__main__":
    mcp.run()
