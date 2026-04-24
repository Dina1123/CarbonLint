"""Kiro tool entry points: optimize_code, compare_versions, and run_pipeline orchestrator."""
from typing import Union
from core.models import Report, ErrorResponse
from core.ast_analyzer import analyze_efficiency
from core.carbon import estimate_carbon
from core.optimizer import optimize_code
from core.comparator import compare_versions

__all__ = ["optimize_code", "compare_versions", "run_pipeline"]


def run_pipeline(code: str) -> Union[Report, ErrorResponse]:
    """Execute the full 5-step optimization pipeline and return a Report."""

    # Step 1: analyze_efficiency
    analysis = analyze_efficiency(code)
    if isinstance(analysis, ErrorResponse):
        return ErrorResponse(
            tool="pipeline",
            message=f"Pipeline failed at analyze_efficiency: {analysis.message}",
            error_type="PipelineError",
        )

    # Step 2: estimate_carbon (original)
    original_metrics = estimate_carbon(code)
    if isinstance(original_metrics, ErrorResponse):
        return ErrorResponse(
            tool="pipeline",
            message=f"Pipeline failed at estimate_carbon (original): {original_metrics.message}",
            error_type="PipelineError",
        )

    # Step 3: optimize_code — pass the ORIGINAL code byte-for-byte
    optimization = optimize_code(code, goal="reduce_energy")
    if isinstance(optimization, ErrorResponse):
        return ErrorResponse(
            tool="pipeline",
            message=f"Pipeline failed at optimize_code: {optimization.message}",
            error_type="PipelineError",
        )

    optimized_code_str = optimization.optimized_code

    # Step 4: estimate_carbon (optimized)
    optimized_metrics = estimate_carbon(optimized_code_str)
    if isinstance(optimized_metrics, ErrorResponse):
        return ErrorResponse(
            tool="pipeline",
            message=f"Pipeline failed at estimate_carbon (optimized): {optimized_metrics.message}",
            error_type="PipelineError",
        )

    # Step 5: compare_versions
    comparison = compare_versions(original_metrics, optimized_metrics)
    if isinstance(comparison, ErrorResponse):
        return ErrorResponse(
            tool="pipeline",
            message=f"Pipeline failed at compare_versions: {comparison.message}",
            error_type="PipelineError",
        )

    return Report(
        analysis=analysis,
        original_metrics=original_metrics,
        optimized_code=optimized_code_str,
        optimized_metrics=optimized_metrics,
        comparison=comparison,
    )
