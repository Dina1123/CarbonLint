"""Comparator for original vs optimized Metrics."""

from typing import Union
from core.models import Metrics, Comparison, ErrorResponse

_REQUIRED_FIELDS = [
    "execution_time_ms",
    "memory_used_bytes",
    "energy_kwh",
    "co2_grams",
]


def _calc_improvement(original_val: float, optimized_val: float) -> float:
    if original_val == 0:
        return 0.0
    return round(((original_val - optimized_val) / original_val) * 100, 2)


def compare_versions(original: Metrics, optimized: Metrics) -> Union[Comparison, ErrorResponse]:
    """Compare original and optimized Metrics, return percentage improvements."""
    # Validate original fields first
    for field_name in _REQUIRED_FIELDS:
        if getattr(original, field_name, None) is None:
            return ErrorResponse(
                tool="compare_versions",
                message=f"Missing required field: '{field_name}'",
                error_type="ValidationError",
            )

    # Then validate optimized fields
    for field_name in _REQUIRED_FIELDS:
        if getattr(optimized, field_name, None) is None:
            return ErrorResponse(
                tool="compare_versions",
                message=f"Missing required field: '{field_name}'",
                error_type="ValidationError",
            )

    execution_time_improvement_pct = _calc_improvement(
        original.execution_time_ms, optimized.execution_time_ms
    )
    memory_improvement_pct = _calc_improvement(
        original.memory_used_bytes, optimized.memory_used_bytes
    )
    co2_improvement_pct = _calc_improvement(original.co2_grams, optimized.co2_grams)

    co2_reduction_grams = original.co2_grams - optimized.co2_grams
    summary = (
        f"Optimization reduced estimated CO\u2082 emissions by "
        f"{co2_reduction_grams:.6f} grams ({co2_improvement_pct:.2f}%). "
        f"Execution time improved by {execution_time_improvement_pct:.2f}% and "
        f"memory usage improved by {memory_improvement_pct:.2f}%."
    )

    return Comparison(
        execution_time_improvement_pct=execution_time_improvement_pct,
        memory_improvement_pct=memory_improvement_pct,
        co2_improvement_pct=co2_improvement_pct,
        summary=summary,
    )
