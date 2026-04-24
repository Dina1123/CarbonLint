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

    all_issues = loop_visitor.issues + expr_visitor.issues
    sorted_issues = sorted(
        all_issues,
        key=lambda i: (_SEVERITY_ORDER.get(i.carbon_impact_score, 99), i.line_number),
    )

    return AnalysisResult(
        functions=functions,
        issues=sorted_issues,
        parse_time_ms=parse_time_ms,
    )
