"""AST-based code efficiency analyzer."""

import ast
import time
from typing import Union

from core.models import AnalysisResult, ErrorResponse, FunctionInfo, Issue
from core.complexity import compute_complexity

_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


class _LoopDepthVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []
        self._loop_depth = 0

    def _visit_loop(self, node):
        self._loop_depth += 1
        if self._loop_depth >= 2:
            self.issues.append(Issue(
                issue_id=f"nested-loop-L{node.lineno}",
                severity="HIGH",
                line_number=node.lineno,
                description=f"Nested loop of depth {self._loop_depth} detected.",
                suggested_fix="Consider flattening the loop or using a hashmap/set to reduce complexity.",
                carbon_impact_score="HIGH",
            ))
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_For(self, node):
        self._visit_loop(node)

    def visit_While(self, node):
        self._visit_loop(node)


class _RepeatedExprVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []

    def _check_loop_body(self, body, loop_lineno):
        expr_counts = {}
        for stmt in ast.walk(ast.Module(body=body, type_ignores=[])):
            for node in ast.walk(stmt):
                if isinstance(node, ast.expr) and not isinstance(node, (ast.Name, ast.Constant)):
                    key = ast.dump(node)
                    expr_counts[key] = expr_counts.get(key, 0) + 1
        for key, count in expr_counts.items():
            if count >= 2:
                self.issues.append(Issue(
                    issue_id=f"repeated-expr-L{loop_lineno}",
                    severity="MEDIUM",
                    line_number=loop_lineno,
                    description=f"Repeated sub-expression detected inside loop body ({count} occurrences).",
                    suggested_fix="Cache the result in a variable before the loop or hoist the expression.",
                    carbon_impact_score="MEDIUM",
                ))
                break  # one issue per loop is enough

    def visit_For(self, node):
        self._check_loop_body(node.body, node.lineno)
        self.generic_visit(node)

    def visit_While(self, node):
        self._check_loop_body(node.body, node.lineno)
        self.generic_visit(node)


class _SortInLoopVisitor(ast.NodeVisitor):
    """Detect sorted() or .sort() called inside a loop — O(n² log n) total."""

    def __init__(self):
        self.issues: list = []
        self._in_loop = False
        self._loop_lineno = 0

    def _enter_loop(self, node) -> None:
        prev, prev_ln = self._in_loop, self._loop_lineno
        self._in_loop = True
        self._loop_lineno = node.lineno
        self.generic_visit(node)
        self._in_loop, self._loop_lineno = prev, prev_ln

    def visit_For(self, node): self._enter_loop(node)
    def visit_While(self, node): self._enter_loop(node)

    def visit_Call(self, node):
        if self._in_loop:
            is_sorted = isinstance(node.func, ast.Name) and node.func.id == 'sorted'
            is_sort   = isinstance(node.func, ast.Attribute) and node.func.attr == 'sort'
            if is_sorted or is_sort:
                label = 'sorted()' if is_sorted else '.sort()'
                self.issues.append(Issue(
                    issue_id=f"sort-in-loop-L{node.lineno}",
                    severity="HIGH",
                    line_number=node.lineno,
                    description=f"Calling {label} inside a loop produces O(n² log n) total complexity.",
                    suggested_fix="Sort the collection once before the loop, or use heapq to maintain order incrementally.",
                    carbon_impact_score="HIGH",
                ))
        self.generic_visit(node)


class _OpenInLoopVisitor(ast.NodeVisitor):
    """Detect open() calls inside a loop — repeated disk I/O per iteration."""

    def __init__(self):
        self.issues: list = []
        self._in_loop = False

    def _enter_loop(self, node) -> None:
        prev = self._in_loop
        self._in_loop = True
        self.generic_visit(node)
        self._in_loop = prev

    def visit_For(self, node): self._enter_loop(node)
    def visit_While(self, node): self._enter_loop(node)

    def visit_Call(self, node):
        if self._in_loop and isinstance(node.func, ast.Name) and node.func.id == 'open':
            self.issues.append(Issue(
                issue_id=f"open-in-loop-L{node.lineno}",
                severity="HIGH",
                line_number=node.lineno,
                description="Opening a file inside a loop performs expensive I/O on every iteration.",
                suggested_fix="Open the file once before the loop and pass the handle in, or load all data into memory first.",
                carbon_impact_score="HIGH",
            ))
        self.generic_visit(node)


class _StringConcatInLoopVisitor(ast.NodeVisitor):
    """Detect str += literal inside loops — creates O(n²) string copies."""

    def __init__(self):
        self.issues: list = []
        self._in_loop = False

    def _enter_loop(self, node) -> None:
        prev = self._in_loop
        self._in_loop = True
        self.generic_visit(node)
        self._in_loop = prev

    def visit_For(self, node): self._enter_loop(node)
    def visit_While(self, node): self._enter_loop(node)

    def _is_string_expr(self, node) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if isinstance(node, ast.JoinedStr):  # f-string
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self._is_string_expr(node.left) or self._is_string_expr(node.right)
        return False

    def visit_AugAssign(self, node):
        if self._in_loop and isinstance(node.op, ast.Add) and self._is_string_expr(node.value):
            self.issues.append(Issue(
                issue_id=f"str-concat-loop-L{node.lineno}",
                severity="HIGH",
                line_number=node.lineno,
                description="String concatenation with += inside a loop creates a new string object each iteration (O(n²) memory copies).",
                suggested_fix="Collect parts in a list and join once after the loop: parts.append(x); result = ''.join(parts)",
                carbon_impact_score="HIGH",
            ))
        self.generic_visit(node)


class _RangeLenVisitor(ast.NodeVisitor):
    """Detect `for x in range(len(y))` — misses direct/enumerate iteration."""

    def __init__(self):
        self.issues: list = []

    def visit_For(self, node):
        it = node.iter
        if (
            isinstance(it, ast.Call)
            and isinstance(it.func, ast.Name) and it.func.id == 'range'
            and len(it.args) == 1
            and isinstance(it.args[0], ast.Call)
            and isinstance(it.args[0].func, ast.Name) and it.args[0].func.id == 'len'
        ):
            self.issues.append(Issue(
                issue_id=f"range-len-L{node.lineno}",
                severity="MEDIUM",
                line_number=node.lineno,
                description="range(len(x)) forces an index lookup each iteration when direct iteration is available.",
                suggested_fix="Use 'for item in x:' for values, or 'for i, item in enumerate(x):' when the index is also needed.",
                carbon_impact_score="MEDIUM",
            ))
        self.generic_visit(node)


def analyze_efficiency(code: str) -> Union[AnalysisResult, ErrorResponse]:
    """Parse code, compute complexity, detect issues, return structured result."""
    if not code or not code.strip():
        return ErrorResponse(
            tool="analyze_efficiency",
            message="Code string is empty.",
            error_type="ValueError",
        )

    t0 = time.perf_counter()
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ErrorResponse(
            tool="analyze_efficiency",
            message=f"Syntax error: {e}",
            error_type="SyntaxError",
        )
    parse_time_ms = (time.perf_counter() - t0) * 1000

    functions = compute_complexity(code)

    loop_visitor = _LoopDepthVisitor()
    loop_visitor.visit(tree)

    expr_visitor = _RepeatedExprVisitor()
    expr_visitor.visit(tree)

    sort_visitor = _SortInLoopVisitor()
    sort_visitor.visit(tree)

    open_visitor = _OpenInLoopVisitor()
    open_visitor.visit(tree)

    str_concat_visitor = _StringConcatInLoopVisitor()
    str_concat_visitor.visit(tree)

    range_len_visitor = _RangeLenVisitor()
    range_len_visitor.visit(tree)

    all_issues = (
        loop_visitor.issues
        + expr_visitor.issues
        + sort_visitor.issues
        + open_visitor.issues
        + str_concat_visitor.issues
        + range_len_visitor.issues
    )
    sorted_issues = sorted(
        all_issues,
        key=lambda i: (_SEVERITY_ORDER.get(i.carbon_impact_score, 99), i.line_number),
    )

    return AnalysisResult(
        functions=functions,
        issues=sorted_issues,
        parse_time_ms=parse_time_ms,
    )
