"""Profiler — measures wall-clock time and peak memory for sandboxed code execution."""

from __future__ import annotations

import time
import tracemalloc
from typing import Union

from core.models import ErrorResponse
from sandbox.executor import execute, ExecutionResult


def profile_execution(code: str, timeout_s: float = 5.0) -> Union[dict, ErrorResponse]:
    """Run code in sandbox, measure wall-clock time and peak memory, return raw dict."""
    tracemalloc.start()
    t0 = time.perf_counter()
    result = execute(code, timeout_s=timeout_s)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if isinstance(result, ErrorResponse):
        return result

    # peak is in bytes (parent-process proxy measurement)
    memory_bytes = peak if peak > 0 else 1024 * 1024  # fallback: 1 MB

    return {
        "execution_time_ms": elapsed_ms,
        "memory_used_bytes": memory_bytes,
    }
