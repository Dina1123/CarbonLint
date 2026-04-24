"""Integration test: full pipeline end-to-end with real code."""
import math
import pytest
from tools.optimize import run_pipeline
from core.models import Report, ErrorResponse


# A real Python code sample with a nested loop and list membership test
SAMPLE_CODE = """
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def process(data):
    result = []
    for i in range(len(data)):
        for j in range(len(data)):
            if data[i] in items:
                result.append(data[i] + data[j])
    return result

output = process(list(range(5)))
"""


def test_pipeline_returns_report_with_all_fields():
    """Full pipeline run returns a Report with all five fields populated."""
    result = run_pipeline(SAMPLE_CODE)
    assert isinstance(result, Report), f"Expected Report, got: {result}"
    assert result.analysis is not None
    assert result.original_metrics is not None
    assert result.optimized_code  # non-empty string
    assert result.optimized_metrics is not None
    assert result.comparison is not None


def test_pipeline_metrics_are_non_negative():
    """All metric values in the report are non-negative."""
    result = run_pipeline(SAMPLE_CODE)
    assert isinstance(result, Report)
    for metrics in [result.original_metrics, result.optimized_metrics]:
        assert metrics.execution_time_ms >= 0
        assert metrics.memory_used_bytes >= 0
        assert metrics.energy_kwh >= 0
        assert metrics.co2_grams >= 0


def test_pipeline_co2_improvement_is_finite():
    """co2_improvement_pct is a finite number."""
    result = run_pipeline(SAMPLE_CODE)
    assert isinstance(result, Report)
    assert math.isfinite(result.comparison.co2_improvement_pct)


def test_pipeline_optimized_code_is_valid_python():
    """Optimized code returned by the pipeline is valid Python."""
    import ast
    result = run_pipeline(SAMPLE_CODE)
    assert isinstance(result, Report)
    ast.parse(result.optimized_code)  # raises SyntaxError if invalid


def test_pipeline_analysis_has_issues():
    """Analyzer detects issues in the sample code (nested loop)."""
    result = run_pipeline(SAMPLE_CODE)
    assert isinstance(result, Report)
    # The sample has nested loops — should detect at least one issue
    assert len(result.analysis.issues) >= 1


def test_pipeline_returns_error_on_syntax_error():
    """Pipeline returns ErrorResponse for syntactically invalid code."""
    result = run_pipeline("def foo(:\n    pass")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "PipelineError"
