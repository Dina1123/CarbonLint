"""Sandbox executor — runs user code in an isolated subprocess."""

from __future__ import annotations

import builtins
import io
import multiprocessing
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from typing import Union

# Unix-only resource limits
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

from core.models import ErrorResponse

ALLOWED_MODULES = frozenset([
    "builtins", "math", "itertools", "functools", "collections", "typing",
    "operator", "string", "re", "json", "datetime", "decimal", "fractions",
    "random", "statistics", "heapq", "bisect", "array", "struct", "time", "io",
])


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int


def _child_worker(
    code: str,
    memory_limit_bytes: int,
    result_queue: multiprocessing.Queue,
) -> None:
    """Module-level worker function executed in the child process."""
    # Apply memory limit (Unix only)
    if HAS_RESOURCE:
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        except (ValueError, resource.error):
            pass

    # Block network access — do this before the import hook so socket itself can load
    try:
        import socket as _socket_module
        def _blocked_socket(*args, **kwargs):
            raise OSError("Network access is not allowed")
        _socket_module.socket = _blocked_socket
    except ImportError:
        pass

    # Create and chdir into temp working directory (before the import hook)
    tmpdir = tempfile.mkdtemp()
    try:
        os.chdir(tmpdir)

        # Capture stdout/stderr
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr

        # Install import allowlist hook only around exec() so Python internals
        # (tempfile, io, etc.) are not affected during worker setup.
        _real_import = builtins.__import__

        def _restricted_import(name, *args, **kwargs):
            top_level = name.split(".")[0]
            # Allow private/internal modules (e.g. _io, _abc) — these are Python
            # internals that the interpreter itself needs; they cannot be imported
            # directly from user code anyway because exec() runs in a clean namespace.
            if top_level.startswith("_"):
                return _real_import(name, *args, **kwargs)
            if top_level not in ALLOWED_MODULES:
                raise ImportError(f"Import of '{top_level}' is not allowed.")
            return _real_import(name, *args, **kwargs)

        builtins.__import__ = _restricted_import
        try:
            exec(code, {})  # noqa: S102
            stdout_val = captured_stdout.getvalue()
            stderr_val = captured_stderr.getvalue()
            result_queue.put({"stdout": stdout_val, "stderr": stderr_val, "exit_code": 0})
        except MemoryError:
            result_queue.put({
                "error": True,
                "tool": "sandbox",
                "message": "Memory limit exceeded.",
                "error_type": "MemoryExceededError",
            })
        except ImportError as exc:
            msg = str(exc)
            result_queue.put({
                "error": True,
                "tool": "sandbox",
                "message": msg,
                "error_type": "ImportError",
            })
        except Exception as exc:  # noqa: BLE001
            result_queue.put({
                "error": True,
                "tool": "sandbox",
                "message": str(exc),
                "error_type": type(exc).__name__,
            })
        finally:
            builtins.__import__ = _real_import
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def execute(
    code: str,
    timeout_s: float = 5.0,
    memory_limit_bytes: int = 256 * 1024 * 1024,
) -> Union[ExecutionResult, ErrorResponse]:
    """Execute code string in an isolated subprocess with resource constraints."""
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()
    process = ctx.Process(
        target=_child_worker,
        args=(code, memory_limit_bytes, result_queue),
    )
    process.start()
    try:
        result = result_queue.get(timeout=timeout_s)
        if isinstance(result, dict) and result.get("error"):
            return ErrorResponse(
                tool="sandbox",
                message=result.get("message", "Unknown error"),
                error_type=result.get("error_type", "ExecutionError"),
            )
        return ExecutionResult(**result)
    except Exception:  # noqa: BLE001 — covers queue.Empty and anything else
        process.terminate()
        return ErrorResponse(
            tool="sandbox",
            message=f"Execution timed out after {timeout_s} seconds.",
            error_type="TimeoutError",
        )
    finally:
        process.terminate()
        process.join()
