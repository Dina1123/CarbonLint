"""Unit tests for the agent pipeline (tools/optimize.py::run_pipeline)."""
from unittest.mock import patch, MagicMock
import pytest
from tools.optimize import run_pipeline
from core.models import (
    Report, ErrorResponse, AnalysisResult, Metrics, OptimizationResult,
    Comparison, FunctionInfo, Change
)


def _make_analysis():
    return AnalysisResult(functions=[], issues=[], parse_time_ms=1.0)

def _make_metrics(exec_ms=100.0, mem=2048, energy=0.001, co2=0.5):
    return Metrics(execution_time_ms=exec_ms, memory_used_bytes=mem, energy_kwh=energy, co2_grams=co2)

def _make_optimization(code="x = 1"):
    return OptimizationResult(optimized_code=code, changes=[], expected_improvement_percent=0.0)

def _make_comparison():
    return Comparison(
        execution_time_improvement_pct=10.0,
        memory_improvement_pct=5.0,
        co2_improvement_pct=8.0,
        summary="Good improvement.",
    )


# Test 1: successful run returns Report with all five fields populated
@patch("tools.optimize.compare_versions")
@patch("tools.optimize.estimate_carbon")
@patch("tools.optimize.optimize_code")
@patch("tools.optimize.analyze_efficiency")
def test_successful_pipeline_returns_report(mock_analyze, mock_optimize, mock_estimate, mock_compare):
    mock_analyze.return_value = _make_analysis()
    mock_estimate.side_effect = [_make_metrics(exec_ms=100.0), _make_metrics(exec_ms=80.0)]
    mock_optimize.return_value = _make_optimization("x = 2")
    mock_compare.return_value = _make_comparison()

    result = run_pipeline("x = 1")
    assert isinstance(result, Report)
    assert result.analysis is not None
    assert result.original_metrics is not None
    assert result.optimized_code == "x = 2"
    assert result.optimized_metrics is not None
    assert result.comparison is not None


# Test 2: analyze_efficiency error → pipeline halts at step 1
@patch("tools.optimize.analyze_efficiency")
def test_pipeline_halts_on_analyze_error(mock_analyze):
    mock_analyze.return_value = ErrorResponse(tool="analyze_efficiency", message="Syntax error", error_type="SyntaxError")
    result = run_pipeline("def foo(:")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "PipelineError"
    assert "analyze_efficiency" in result.message


# Test 3: first estimate_carbon error → pipeline halts at step 2
@patch("tools.optimize.estimate_carbon")
@patch("tools.optimize.analyze_efficiency")
def test_pipeline_halts_on_first_estimate_error(mock_analyze, mock_estimate):
    mock_analyze.return_value = _make_analysis()
    mock_estimate.return_value = ErrorResponse(tool="estimate_carbon", message="Timeout", error_type="TimeoutError")
    result = run_pipeline("x = 1")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "PipelineError"
    assert "estimate_carbon" in result.message


# Test 4: optimize_code error → pipeline halts at step 3
@patch("tools.optimize.optimize_code")
@patch("tools.optimize.estimate_carbon")
@patch("tools.optimize.analyze_efficiency")
def test_pipeline_halts_on_optimize_error(mock_analyze, mock_estimate, mock_optimize):
    mock_analyze.return_value = _make_analysis()
    mock_estimate.return_value = _make_metrics()
    mock_optimize.return_value = ErrorResponse(tool="optimize_code", message="Failed", error_type="ValueError")
    result = run_pipeline("x = 1")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "PipelineError"
    assert "optimize_code" in result.message


# Test 5: second estimate_carbon error → pipeline halts at step 4
@patch("tools.optimize.compare_versions")
@patch("tools.optimize.estimate_carbon")
@patch("tools.optimize.optimize_code")
@patch("tools.optimize.analyze_efficiency")
def test_pipeline_halts_on_second_estimate_error(mock_analyze, mock_optimize, mock_estimate, mock_compare):
    mock_analyze.return_value = _make_analysis()
    mock_estimate.side_effect = [_make_metrics(), ErrorResponse(tool="estimate_carbon", message="Timeout", error_type="TimeoutError")]
    mock_optimize.return_value = _make_optimization()
    result = run_pipeline("x = 1")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "PipelineError"


# Test 6: code passed to optimize_code is identical to code passed to first estimate_carbon
@patch("tools.optimize.compare_versions")
@patch("tools.optimize.estimate_carbon")
@patch("tools.optimize.optimize_code")
@patch("tools.optimize.analyze_efficiency")
def test_pipeline_code_immutability(mock_analyze, mock_optimize, mock_estimate, mock_compare):
    original_code = "for i in range(10):\n    pass"
    mock_analyze.return_value = _make_analysis()
    mock_estimate.side_effect = [_make_metrics(), _make_metrics()]
    mock_optimize.return_value = _make_optimization(original_code)
    mock_compare.return_value = _make_comparison()

    run_pipeline(original_code)

    # The code passed to the first estimate_carbon call must be the original
    first_estimate_call_code = mock_estimate.call_args_list[0][0][0]
    optimize_call_code = mock_optimize.call_args_list[0][0][0]
    assert first_estimate_call_code == original_code
    assert optimize_call_code == original_code


# Test 7: compare_versions error → pipeline halts at step 5
@patch("tools.optimize.compare_versions")
@patch("tools.optimize.estimate_carbon")
@patch("tools.optimize.optimize_code")
@patch("tools.optimize.analyze_efficiency")
def test_pipeline_halts_on_compare_error(mock_analyze, mock_optimize, mock_estimate, mock_compare):
    mock_analyze.return_value = _make_analysis()
    mock_estimate.side_effect = [_make_metrics(), _make_metrics()]
    mock_optimize.return_value = _make_optimization()
    mock_compare.return_value = ErrorResponse(tool="compare_versions", message="Missing field", error_type="ValidationError")
    result = run_pipeline("x = 1")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "PipelineError"
    assert "compare_versions" in result.message
