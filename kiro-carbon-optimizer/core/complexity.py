"""Cyclomatic complexity computation using radon."""

from core.models import FunctionInfo


def compute_complexity(code: str) -> list[FunctionInfo]:
    """Use radon to compute cyclomatic complexity per function."""
    if not code or not code.strip():
        return []
    try:
        from radon.complexity import cc_visit
        results = cc_visit(code)
        return [
            FunctionInfo(
                name=r.name,
                complexity_score=r.complexity,
                line_start=r.lineno,
                line_end=r.endline,
            )
            for r in results
        ]
    except Exception:
        return []
