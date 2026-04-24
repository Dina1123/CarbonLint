"""Unit tests for core/models.py — serialisation round-trips."""

import pytest
from core.models import (
    AnalysisResult,
    Change,
    Comparison,
    ConfigIssue,
    ErrorResponse,
    FunctionInfo,
    Issue,
    MCPSuggestion,
    Metrics,
    OptimizationResult,
    Report,
    StruggleSignal,
)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_metrics_round_trip():
    m = Metrics(execution_time_ms=42.5, memory_used_bytes=1048576, energy_kwh=0.000001234, co2_grams=0.000567)
    assert Metrics.from_dict(m.to_dict()) == m


# ---------------------------------------------------------------------------
# FunctionInfo
# ---------------------------------------------------------------------------

def test_function_info_round_trip():
    fi = FunctionInfo(name="process_data", complexity_score=8, line_start=5, line_end=20)
    assert FunctionInfo.from_dict(fi.to_dict()) == fi


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------

def test_issue_round_trip():
    issue = Issue(
        issue_id="nested-loop-L12",
        severity="HIGH",
        line_number=12,
        description="Nested loop detected.",
        suggested_fix="Use list comprehension.",
        carbon_impact_score="HIGH",
    )
    assert Issue.from_dict(issue.to_dict()) == issue


# ---------------------------------------------------------------------------
# AnalysisResult (nested)
# ---------------------------------------------------------------------------

def test_analysis_result_round_trip_empty():
    ar = AnalysisResult()
    assert AnalysisResult.from_dict(ar.to_dict()) == ar


def test_analysis_result_round_trip_with_nested():
    ar = AnalysisResult(
        functions=[FunctionInfo(name="foo", complexity_score=3, line_start=1, line_end=10)],
        issues=[
            Issue(
                issue_id="nested-loop-L5",
                severity="HIGH",
                line_number=5,
                description="Nested loop.",
                suggested_fix="Flatten it.",
                carbon_impact_score="HIGH",
            )
        ],
        parse_time_ms=12.3,
    )
    reconstructed = AnalysisResult.from_dict(ar.to_dict())
    assert reconstructed == ar
    assert isinstance(reconstructed.functions[0], FunctionInfo)
    assert isinstance(reconstructed.issues[0], Issue)


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------

def test_change_round_trip():
    c = Change(pass_name="AlgorithmicSubstitutionPass", description="Replaced list with set.", line_number=14)
    assert Change.from_dict(c.to_dict()) == c


# ---------------------------------------------------------------------------
# OptimizationResult (nested)
# ---------------------------------------------------------------------------

def test_optimization_result_round_trip():
    opt = OptimizationResult(
        optimized_code="def foo(): pass",
        changes=[Change(pass_name="MemoizationPass", description="Added lru_cache.", line_number=3)],
        expected_improvement_percent=35.0,
    )
    reconstructed = OptimizationResult.from_dict(opt.to_dict())
    assert reconstructed == opt
    assert isinstance(reconstructed.changes[0], Change)


def test_optimization_result_empty_changes():
    opt = OptimizationResult(optimized_code="x = 1")
    assert OptimizationResult.from_dict(opt.to_dict()) == opt


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def test_comparison_round_trip():
    comp = Comparison(
        execution_time_improvement_pct=42.10,
        memory_improvement_pct=15.30,
        co2_improvement_pct=38.75,
        summary="Reduced CO₂ by 38.75%.",
    )
    assert Comparison.from_dict(comp.to_dict()) == comp


# ---------------------------------------------------------------------------
# Report (deeply nested)
# ---------------------------------------------------------------------------

def test_report_round_trip():
    report = Report(
        analysis=AnalysisResult(
            functions=[FunctionInfo(name="bar", complexity_score=5, line_start=1, line_end=8)],
            issues=[],
            parse_time_ms=5.0,
        ),
        original_metrics=Metrics(execution_time_ms=100.0, memory_used_bytes=2048, energy_kwh=0.001, co2_grams=0.5),
        optimized_code="def bar(): pass",
        optimized_metrics=Metrics(execution_time_ms=58.0, memory_used_bytes=1024, energy_kwh=0.0006, co2_grams=0.3),
        comparison=Comparison(
            execution_time_improvement_pct=42.0,
            memory_improvement_pct=50.0,
            co2_improvement_pct=40.0,
            summary="Good improvement.",
        ),
    )
    reconstructed = Report.from_dict(report.to_dict())
    assert reconstructed == report
    assert isinstance(reconstructed.analysis, AnalysisResult)
    assert isinstance(reconstructed.original_metrics, Metrics)
    assert isinstance(reconstructed.comparison, Comparison)


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------

def test_error_response_always_has_error_true():
    er = ErrorResponse(tool="estimate_carbon", message="Timed out.")
    assert er.error is True


def test_error_response_round_trip():
    er = ErrorResponse(tool="estimate_carbon", message="Timed out.", error_type="TimeoutError")
    reconstructed = ErrorResponse.from_dict(er.to_dict())
    assert reconstructed == er
    assert reconstructed.error is True


def test_error_response_from_dict_defaults_error_true():
    d = {"tool": "analyze_efficiency", "message": "Syntax error.", "error_type": "SyntaxError"}
    er = ErrorResponse.from_dict(d)
    assert er.error is True


# ---------------------------------------------------------------------------
# MCPSuggestion
# ---------------------------------------------------------------------------

def test_mcp_suggestion_round_trip():
    mcp = MCPSuggestion(server="Context7 MCP", reason="API confusion detected.")
    assert MCPSuggestion.from_dict(mcp.to_dict()) == mcp


# ---------------------------------------------------------------------------
# StruggleSignal (with and without mcp_suggestion)
# ---------------------------------------------------------------------------

def test_struggle_signal_round_trip_with_mcp():
    sig = StruggleSignal(
        signal_type="repeated_prompt_loop",
        severity="medium",
        message="You may be in a retry loop.",
        mcp_suggestion=MCPSuggestion(server="Context7 MCP", reason="API confusion."),
    )
    reconstructed = StruggleSignal.from_dict(sig.to_dict())
    assert reconstructed == sig
    assert isinstance(reconstructed.mcp_suggestion, MCPSuggestion)


def test_struggle_signal_round_trip_without_mcp():
    sig = StruggleSignal(
        signal_type="oversized_prompt",
        severity="low",
        message="Prompt is very long.",
        mcp_suggestion=None,
    )
    reconstructed = StruggleSignal.from_dict(sig.to_dict())
    assert reconstructed == sig
    assert reconstructed.mcp_suggestion is None


# ---------------------------------------------------------------------------
# ConfigIssue
# ---------------------------------------------------------------------------

def test_config_issue_round_trip():
    ci = ConfigIssue(
        issue_id="unpinned-base-image",
        file_path="Dockerfile",
        line_number=1,
        description="Base image uses 'latest' tag.",
        carbon_impact_score="HIGH",
        remediation="Pin to a specific version.",
        example_fix="FROM python:3.12-slim",
    )
    assert ConfigIssue.from_dict(ci.to_dict()) == ci
