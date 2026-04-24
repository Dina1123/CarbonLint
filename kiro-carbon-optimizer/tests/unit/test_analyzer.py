"""Unit tests for core/ast_analyzer.py."""

import pytest
from core.ast_analyzer import analyze_efficiency
from core.models import AnalysisResult, ErrorResponse


def test_function_count_matches():
    code = "def foo(): pass\ndef bar(): pass"
    result = analyze_efficiency(code)
    assert isinstance(result, AnalysisResult)
    assert len(result.functions) == 2


def test_nested_loop_detected():
    code = "for i in range(10):\n    for j in range(10):\n        pass"
    result = analyze_efficiency(code)
    assert any("nested-loop" in issue.issue_id for issue in result.issues)


def test_no_nested_loop_no_issue():
    code = "for i in range(10):\n    pass"
    result = analyze_efficiency(code)
    assert not any("nested-loop" in issue.issue_id for issue in result.issues)


def test_repeated_subexpr_detected():
    code = "for i in range(10):\n    x = len([1,2,3]) + len([1,2,3])"
    result = analyze_efficiency(code)
    assert any("repeated-expr" in issue.issue_id for issue in result.issues)


def test_empty_code_returns_error():
    result = analyze_efficiency("")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ValueError"


def test_syntax_error_returns_error():
    result = analyze_efficiency("def foo(:\n    pass")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "SyntaxError"


def test_issues_sorted_by_severity():
    code = (
        "for i in range(10):\n"
        "    for j in range(10):\n"
        "        x = len([1,2,3]) + len([1,2,3])\n"
    )
    result = analyze_efficiency(code)
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    scores = [severity_order[issue.carbon_impact_score] for issue in result.issues]
    assert scores == sorted(scores)
