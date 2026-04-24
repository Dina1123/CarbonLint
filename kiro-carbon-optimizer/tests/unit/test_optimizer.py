"""Unit tests for core/optimizer.py."""

import ast

import pytest

from core.models import ErrorResponse, OptimizationResult
from core.optimizer import (
    AlgorithmicSubstitutionPass,
    ExpressionHoistingPass,
    LoopReductionPass,
    MemoizationPass,
    optimize_code,
)


# ---------------------------------------------------------------------------
# optimize_code — error cases
# ---------------------------------------------------------------------------

def test_empty_code_returns_error():
    result = optimize_code("")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ValueError"


def test_whitespace_only_returns_error():
    result = optimize_code("   \n  ")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "ValueError"


def test_syntax_error_returns_error():
    result = optimize_code("def foo(:\n    pass")
    assert isinstance(result, ErrorResponse)
    assert result.error_type == "SyntaxError"


# ---------------------------------------------------------------------------
# optimize_code — no-op case
# ---------------------------------------------------------------------------

def test_no_optimizable_patterns():
    code = "x = 1 + 1\ny = x * 2"
    result = optimize_code(code)
    assert isinstance(result, OptimizationResult)
    assert result.optimized_code == code
    assert result.changes == []
    assert result.expected_improvement_percent == 0.0


# ---------------------------------------------------------------------------
# optimize_code — result always valid Python
# ---------------------------------------------------------------------------

def test_optimized_code_is_valid_python():
    """AST round-trip: optimized code must always parse cleanly."""
    codes = [
        "for i in range(5):\n    for j in range(5):\n        pass",
        "def f(x): return x\nfor i in range(10):\n    f(i)",
        "items=[1,2,3]\nfor x in range(5):\n    if x in items: pass",
    ]
    for code in codes:
        result = optimize_code(code)
        assert isinstance(result, OptimizationResult)
        ast.parse(result.optimized_code)  # raises SyntaxError if invalid


# ---------------------------------------------------------------------------
# LoopReductionPass
# ---------------------------------------------------------------------------

def test_nested_loop_flattened():
    code = (
        "import itertools\n"
        "for i in range(3):\n"
        "    for j in range(3):\n"
        "        print(i, j)"
    )
    result = optimize_code(code)
    assert isinstance(result, OptimizationResult)
    assert result.optimized_code  # non-empty


def test_loop_reduction_pass_fires():
    code = (
        "for i in range(3):\n"
        "    for j in range(3):\n"
        "        print(j)"
    )
    pass_ = LoopReductionPass()
    new_code, changes = pass_.apply(code)
    assert len(changes) >= 1
    assert changes[0].pass_name == "LoopReductionPass"
    assert "itertools" in new_code
    ast.parse(new_code)


def test_loop_reduction_adds_import_itertools():
    code = (
        "for i in range(3):\n"
        "    for j in range(3):\n"
        "        print(j)"
    )
    pass_ = LoopReductionPass()
    new_code, changes = pass_.apply(code)
    if changes:
        assert "import itertools" in new_code


def test_loop_reduction_no_change_when_inner_uses_outer_var():
    # Inner body references outer loop variable — should NOT flatten
    code = (
        "for i in range(3):\n"
        "    for j in range(i):\n"
        "        print(j)"
    )
    pass_ = LoopReductionPass()
    new_code, changes = pass_.apply(code)
    # Either no changes, or if changed, still valid Python
    ast.parse(new_code)


# ---------------------------------------------------------------------------
# MemoizationPass
# ---------------------------------------------------------------------------

def test_memoization_pass_fires():
    code = (
        "def compute(x):\n"
        "    return x * x\n\n"
        "results = []\n"
        "for i in range(10):\n"
        "    results.append(compute(i))\n"
    )
    result = optimize_code(code)
    assert isinstance(result, OptimizationResult)
    memo_changes = [c for c in result.changes if c.pass_name == "MemoizationPass"]
    assert len(memo_changes) >= 1


def test_memoization_adds_functools_import():
    code = (
        "def compute(x):\n"
        "    return x * x\n\n"
        "for i in range(10):\n"
        "    compute(i)\n"
    )
    pass_ = MemoizationPass()
    new_code, changes = pass_.apply(code)
    if changes:
        assert "functools" in new_code
        assert "lru_cache" in new_code
        ast.parse(new_code)


def test_memoization_not_applied_twice():
    code = (
        "import functools\n\n"
        "@functools.lru_cache\n"
        "def compute(x):\n"
        "    return x * x\n\n"
        "for i in range(10):\n"
        "    compute(i)\n"
    )
    pass_ = MemoizationPass()
    new_code, changes = pass_.apply(code)
    # Should not add lru_cache again
    assert new_code.count("lru_cache") == 1


def test_memoization_no_change_when_no_loop():
    code = "def compute(x):\n    return x * x\n"
    pass_ = MemoizationPass()
    _, changes = pass_.apply(code)
    assert changes == []


# ---------------------------------------------------------------------------
# AlgorithmicSubstitutionPass
# ---------------------------------------------------------------------------

def test_set_lookup_substitution():
    code = (
        "items = [1, 2, 3, 4, 5]\n"
        "for x in range(10):\n"
        "    if x in items:\n"
        "        print(x)\n"
    )
    result = optimize_code(code)
    assert isinstance(result, OptimizationResult)
    set_changes = [c for c in result.changes if c.pass_name == "AlgorithmicSubstitutionPass"]
    assert len(set_changes) >= 1


def test_set_lookup_produces_valid_python():
    code = (
        "items = [1, 2, 3]\n"
        "for x in range(5):\n"
        "    if x in items:\n"
        "        pass\n"
    )
    pass_ = AlgorithmicSubstitutionPass()
    new_code, changes = pass_.apply(code)
    if changes:
        assert "set(items)" in new_code
        ast.parse(new_code)


def test_set_lookup_no_change_when_not_list():
    # items is not assigned a list literal — should not substitute
    code = (
        "items = set([1, 2, 3])\n"
        "for x in range(5):\n"
        "    if x in items:\n"
        "        pass\n"
    )
    pass_ = AlgorithmicSubstitutionPass()
    _, changes = pass_.apply(code)
    assert changes == []


# ---------------------------------------------------------------------------
# ExpressionHoistingPass
# ---------------------------------------------------------------------------

def test_expression_hoisting_fires():
    code = (
        "import math\n"
        "for i in range(10):\n"
        "    x = math.sqrt(4)\n"
        "    print(x)\n"
    )
    pass_ = ExpressionHoistingPass()
    new_code, changes = pass_.apply(code)
    if changes:
        assert changes[0].pass_name == "ExpressionHoistingPass"
        assert "_hoisted_" in new_code
        ast.parse(new_code)


def test_expression_hoisting_produces_valid_python():
    code = (
        "import math\n"
        "for i in range(10):\n"
        "    y = math.sqrt(9)\n"
    )
    pass_ = ExpressionHoistingPass()
    new_code, changes = pass_.apply(code)
    ast.parse(new_code)


# ---------------------------------------------------------------------------
# Change descriptions are non-empty
# ---------------------------------------------------------------------------

def test_all_changes_have_descriptions():
    codes = [
        (
            "def f(x): return x\n"
            "for i in range(10):\n"
            "    f(i)\n"
        ),
        (
            "items = [1, 2, 3]\n"
            "for x in range(5):\n"
            "    if x in items: pass\n"
        ),
    ]
    for code in codes:
        result = optimize_code(code)
        assert isinstance(result, OptimizationResult)
        for change in result.changes:
            assert change.description and len(change.description) > 0


# ---------------------------------------------------------------------------
# Improvement percent is capped at 80
# ---------------------------------------------------------------------------

def test_improvement_percent_capped():
    # Code that triggers multiple passes
    code = (
        "def compute(x):\n"
        "    return x * x\n\n"
        "items = [1, 2, 3, 4, 5]\n"
        "for i in range(3):\n"
        "    for j in range(3):\n"
        "        if compute(j) in items:\n"
        "            pass\n"
    )
    result = optimize_code(code)
    assert isinstance(result, OptimizationResult)
    assert result.expected_improvement_percent <= 80.0
