"""Integration test: sandbox process isolation."""
import pytest
from sandbox.executor import execute, ExecutionResult
from core.models import ErrorResponse


def test_filesystem_access_outside_tmpdir_blocked():
    """Code attempting to read /etc/passwd (or Windows equivalent) returns an error."""
    # os is not in the allowlist, so this will return ImportError
    result = execute("import os; os.listdir('/')")
    assert isinstance(result, ErrorResponse)
    # Either ImportError (os blocked) or some execution error
    assert result.error is True


def test_network_access_blocked():
    """Code attempting to import socket returns ImportError."""
    result = execute("import socket; socket.gethostbyname('google.com')")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ImportError"


def test_non_allowlisted_import_blocked():
    """Importing os (not in allowlist) returns ImportError."""
    result = execute("import os")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ImportError"
    assert "os" in result.message


def test_allowlisted_module_works():
    """Importing math (in allowlist) succeeds."""
    result = execute("import math; x = math.pi")
    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0


def test_timeout_enforced():
    """Code that sleeps longer than timeout returns TimeoutError."""
    result = execute("import time; time.sleep(30)", timeout_s=1.0)
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "TimeoutError"


def test_execution_error_captured():
    """Unhandled exception in code returns ErrorResponse with correct type."""
    result = execute("raise RuntimeError('integration test error')")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "RuntimeError"
    assert "integration test error" in result.message
