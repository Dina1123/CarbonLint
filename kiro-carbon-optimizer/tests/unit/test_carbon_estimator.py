"""Unit tests for the Carbon Estimator (core/carbon.py and core/profiler.py)."""

import pytest
from core.carbon import estimate_carbon
from core.profiler import profile_execution
from core.models import Metrics, ErrorResponse
from sandbox.executor import ExecutionResult


# Test 1: valid code returns all four Metrics fields as non-negative numbers
def test_valid_code_returns_metrics():
    result = estimate_carbon("x = 1 + 1")
    assert isinstance(result, Metrics)
    assert result.execution_time_ms >= 0
    assert result.memory_used_bytes >= 0
    assert result.energy_kwh >= 0
    assert result.co2_grams >= 0


# Test 2: code raising an exception returns ErrorResponse with exception type
def test_exception_in_code_returns_error():
    result = estimate_carbon('raise ValueError("test")')
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ValueError"


# Test 3: timeout returns ErrorResponse with TimeoutError
def test_timeout_returns_error():
    result = estimate_carbon("import time; time.sleep(10)", timeout_s=1.0)
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "TimeoutError"


# Test 4: all four Metrics fields are present and non-negative
def test_metrics_fields_non_negative():
    result = estimate_carbon("result = sum(range(100))")
    assert isinstance(result, Metrics)
    assert all(v >= 0 for v in [
        result.execution_time_ms,
        result.memory_used_bytes,
        result.energy_kwh,
        result.co2_grams,
    ])


# Test 5: profile_execution propagates ErrorResponse from sandbox
def test_profile_execution_propagates_error():
    result = profile_execution('raise RuntimeError("boom")')
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "RuntimeError"


# Test 6: profile_execution returns dict with expected keys for valid code
def test_profile_execution_returns_dict():
    result = profile_execution("x = 42")
    assert isinstance(result, dict)
    assert "execution_time_ms" in result
    assert "memory_used_bytes" in result
    assert result["execution_time_ms"] >= 0
    assert result["memory_used_bytes"] >= 0
