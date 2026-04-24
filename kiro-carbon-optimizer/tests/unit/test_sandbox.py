"""Unit tests for sandbox/executor.py."""
import pytest

from sandbox.executor import execute, ExecutionResult
from core.models import ErrorResponse


def test_allowlisted_import_succeeds():
    """math is in the allowlist — should return ExecutionResult."""
    result = execute("import math; result = math.sqrt(4)")
    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0


def test_non_allowlisted_import_raises():
    """os is NOT in the allowlist — should return ErrorResponse with ImportError."""
    result = execute("import os")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ImportError"
    assert "os" in result.message


def test_network_access_blocked():
    """socket is not in the allowlist — should return ErrorResponse."""
    result = execute("import socket")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ImportError"


def test_timeout_returns_error():
    """time.sleep(10) with timeout_s=1.0 should return TimeoutError."""
    result = execute("import time; time.sleep(10)", timeout_s=1.0)
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "TimeoutError"
    assert "timed out" in result.message.lower()


def test_execution_exception_returns_error():
    """Unhandled ValueError should return ErrorResponse with error_type=ValueError."""
    result = execute('raise ValueError("test error")')
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ValueError"
    assert "test error" in result.message


def test_stdout_captured():
    """print() output should be captured in ExecutionResult.stdout."""
    result = execute('print("hello")')
    assert isinstance(result, ExecutionResult)
    assert "hello" in result.stdout
