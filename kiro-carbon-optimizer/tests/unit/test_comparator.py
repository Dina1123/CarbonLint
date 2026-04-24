"""Unit tests for core/comparator.py."""

import pytest
from core.comparator import compare_versions
from core.models import Metrics, Comparison, ErrorResponse


def make_metrics(exec_ms=100.0, mem=2048, energy=0.001, co2=0.5):
    return Metrics(execution_time_ms=exec_ms, memory_used_bytes=mem, energy_kwh=energy, co2_grams=co2)


def test_valid_comparison_returns_comparison():
    orig = make_metrics(exec_ms=100.0, co2=0.5)
    opt = make_metrics(exec_ms=75.0, co2=0.3)
    result = compare_versions(orig, opt)
    assert isinstance(result, Comparison)
    assert result.execution_time_improvement_pct == 25.0
    assert result.co2_improvement_pct == 40.0
    assert result.summary  # non-empty


def test_negative_improvement_when_optimized_worse():
    orig = make_metrics(exec_ms=100.0)
    opt = make_metrics(exec_ms=150.0)
    result = compare_versions(orig, opt)
    assert isinstance(result, Comparison)
    assert result.execution_time_improvement_pct == -50.0


def test_formula_correctness():
    orig = make_metrics(exec_ms=200.0, mem=4096, co2=1.0)
    opt = make_metrics(exec_ms=100.0, mem=2048, co2=0.6)
    result = compare_versions(orig, opt)
    assert result.execution_time_improvement_pct == 50.0
    assert result.memory_improvement_pct == 50.0
    assert result.co2_improvement_pct == 40.0


def test_zero_original_value_no_error():
    orig = make_metrics(exec_ms=0.0)
    opt = make_metrics(exec_ms=50.0)
    result = compare_versions(orig, opt)
    assert isinstance(result, Comparison)
    assert result.execution_time_improvement_pct == 0.0


def test_missing_field_in_original():
    orig = Metrics(execution_time_ms=None, memory_used_bytes=2048, energy_kwh=0.001, co2_grams=0.5)
    opt = make_metrics()
    result = compare_versions(orig, opt)
    assert isinstance(result, ErrorResponse)
    assert "execution_time_ms" in result.message


def test_missing_field_in_optimized():
    orig = make_metrics()
    opt = Metrics(execution_time_ms=50.0, memory_used_bytes=1024, energy_kwh=0.0005, co2_grams=None)
    result = compare_versions(orig, opt)
    assert isinstance(result, ErrorResponse)
    assert "co2_grams" in result.message


def test_summary_contains_co2():
    orig = make_metrics(co2=1.0)
    opt = make_metrics(co2=0.6)
    result = compare_versions(orig, opt)
    assert isinstance(result, Comparison)
    assert "CO" in result.summary or "co2" in result.summary.lower() or "emission" in result.summary.lower()


def test_improvement_rounded():
    orig = make_metrics(exec_ms=300.0)
    opt = make_metrics(exec_ms=100.0)
    result = compare_versions(orig, opt)
    assert result.execution_time_improvement_pct == round(((300.0 - 100.0) / 300.0) * 100, 2)
