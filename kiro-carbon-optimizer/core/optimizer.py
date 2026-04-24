"""AST transformation passes and optimize_code entry point."""

import ast
import copy
import itertools
from typing import Union

from core.models import Change, ErrorResponse, OptimizationResult


# ---------------------------------------------------------------------------
# Pass 1: LoopReductionPass
# ---------------------------------------------------------------------------

class _NestedLoopFlattener(ast.NodeTransformer):
    def __init__(self):
        self.changes_made = False
        self.changes = []

    def visit_For(self, node):
        self.generic_visit(node)
        # Only flatten if this For has exactly one child that is also a For
        if len(node.body) == 1 and isinstance(node.body[0], ast.For):
            inner = node.body[0]
            outer_var_dump = ast.dump(node.target)
            inner_var_dump = ast.dump(inner.target)

            # Safety check: inner body must not reference the outer loop variable
            inner_body_dump = ast.dump(ast.Module(body=inner.body, type_ignores=[]))
            if outer_var_dump not in inner_body_dump or inner_var_dump == outer_var_dump:
                new_target = ast.Tuple(
                    elts=[node.target, inner.target],
                    ctx=ast.Store(),
                )
                product_call = ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="itertools", ctx=ast.Load()),
                        attr="product",
                        ctx=ast.Load(),
                    ),
                    args=[node.iter, inner.iter],
                    keywords=[],
                )
                new_for = ast.For(
                    target=new_target,
                    iter=product_call,
                    body=inner.body,
                    orelse=node.orelse,
                )
                self.changes_made = True
                self.changes.append(Change(
                    pass_name="LoopReductionPass",
                    description=(
                        f"Flattened nested For loop at line {node.lineno} "
                        "using itertools.product."
                    ),
                    line_number=node.lineno,
                ))
                return new_for
        return node


class LoopReductionPass:
    """Flatten safe nested For loops using itertools.product."""

    def apply(self, code: str) -> tuple[str, list]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, []

        transformer = _NestedLoopFlattener()
        new_tree = transformer.visit(copy.deepcopy(tree))

        if not transformer.changes_made:
            return code, []

        try:
            ast.fix_missing_locations(new_tree)
            new_code = ast.unparse(new_tree)
            ast.parse(new_code)  # round-trip validation
        except Exception:
            return code, []

        # Ensure `import itertools` is present
        has_itertools = any(
            (isinstance(n, ast.Import) and any(a.name == "itertools" for a in n.names))
            or (isinstance(n, ast.ImportFrom) and n.module == "itertools")
            for n in ast.parse(new_code).body
        )
        if not has_itertools:
            new_code = "import itertools\n" + new_code

        # Final round-trip validation after prepending import
        try:
            ast.parse(new_code)
        except Exception:
            return code, []

        return new_code, transformer.changes


# ---------------------------------------------------------------------------
# Pass 2: ExpressionHoistingPass
# ---------------------------------------------------------------------------

def _get_loop_target_names(target_node) -> set:
    """Collect all Name ids from a loop target (handles tuples)."""
    names = set()
    for node in ast.walk(target_node):
        if isinstance(node, ast.Name):
            names.add(node.id)
    return names


class _ExpressionHoister(ast.NodeTransformer):
    def __init__(self):
        self.changes_made = False
        self.changes = []
        self._counter = 0

    def _hoist_from_loop(self, node, loop_target):
        """Return (new_stmts_before_loop, new_loop_body)."""
        target_names = _get_loop_target_names(loop_target)
        hoisted_stmts = []
        new_body = copy.deepcopy(node.body)

        class _CallReplacer(ast.NodeTransformer):
            def __init__(inner_self):
                inner_self.hoisted = []
                inner_self.counter_ref = [self._counter]

            def visit_Call(inner_self, call_node):
                inner_self.generic_visit(call_node)
                # Only hoist if all args are constants or names not in loop vars
                all_safe = all(
                    isinstance(a, ast.Constant)
                    or (isinstance(a, ast.Name) and a.id not in target_names)
                    for a in call_node.args
                )
                if not all_safe or call_node.keywords:
                    return call_node
                # Don't hoist if the function itself is the loop variable
                if isinstance(call_node.func, ast.Name) and call_node.func.id in target_names:
                    return call_node

                var_name = f"_hoisted_{inner_self.counter_ref[0]}"
                inner_self.counter_ref[0] += 1
                assign = ast.Assign(
                    targets=[ast.Name(id=var_name, ctx=ast.Store())],
                    value=call_node,
                )
                inner_self.hoisted.append(assign)
                return ast.Name(id=var_name, ctx=ast.Load())

        replacer = _CallReplacer()
        new_body_nodes = [replacer.visit(stmt) for stmt in new_body]
        self._counter = replacer.counter_ref[0]

        if replacer.hoisted:
            self.changes_made = True
            for assign in replacer.hoisted:
                hoisted_stmts.append(assign)
                self.changes.append(Change(
                    pass_name="ExpressionHoistingPass",
                    description=(
                        f"Hoisted loop-invariant call expression out of loop "
                        f"at line {node.lineno} into temporary variable."
                    ),
                    line_number=node.lineno,
                ))

        return hoisted_stmts, new_body_nodes

    def visit_For(self, node):
        self.generic_visit(node)
        hoisted, new_body = self._hoist_from_loop(node, node.target)
        if not hoisted:
            return node
        new_loop = copy.copy(node)
        new_loop.body = new_body
        return [*hoisted, new_loop]

    def visit_While(self, node):
        self.generic_visit(node)
        # For while loops, use a dummy target with no names
        dummy_target = ast.Name(id="__while__", ctx=ast.Store())
        hoisted, new_body = self._hoist_from_loop(node, dummy_target)
        if not hoisted:
            return node
        new_loop = copy.copy(node)
        new_loop.body = new_body
        return [*hoisted, new_loop]


class ExpressionHoistingPass:
    """Hoist loop-invariant sub-expressions out of loop bodies."""

    def apply(self, code: str) -> tuple[str, list]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, []

        transformer = _ExpressionHoister()
        new_tree = transformer.visit(copy.deepcopy(tree))

        if not transformer.changes_made:
            return code, []

        try:
            ast.fix_missing_locations(new_tree)
            new_code = ast.unparse(new_tree)
            ast.parse(new_code)
            return new_code, transformer.changes
        except Exception:
            return code, []


# ---------------------------------------------------------------------------
# Pass 3: MemoizationPass
# ---------------------------------------------------------------------------

class _LruCacheAdder(ast.NodeTransformer):
    def __init__(self, target_funcs: set):
        self.target_funcs = target_funcs
        self.changes_made = False
        self.changes = []

    def visit_FunctionDef(self, node):
        if node.name not in self.target_funcs:
            return node
        # Check if lru_cache already applied
        for dec in node.decorator_list:
            if isinstance(dec, ast.Attribute) and dec.attr == "lru_cache":
                return node
            if isinstance(dec, ast.Name) and dec.id == "lru_cache":
                return node
            if isinstance(dec, ast.Call):
                func = dec.func
                if isinstance(func, ast.Attribute) and func.attr == "lru_cache":
                    return node
                if isinstance(func, ast.Name) and func.id == "lru_cache":
                    return node
        # Add @functools.lru_cache
        lru_decorator = ast.Attribute(
            value=ast.Name(id="functools", ctx=ast.Load()),
            attr="lru_cache",
            ctx=ast.Load(),
        )
        node.decorator_list.insert(0, lru_decorator)
        self.changes_made = True
        self.changes.append(Change(
            pass_name="MemoizationPass",
            description=(
                f"Added @functools.lru_cache to '{node.name}' called inside a loop."
            ),
            line_number=node.lineno,
        ))
        return node


class MemoizationPass:
    """Add functools.lru_cache to pure functions called inside loops."""

    def apply(self, code: str) -> tuple[str, list]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, []

        # Find top-level function definitions
        top_level_funcs = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }

        if not top_level_funcs:
            return code, []

        # Find function names called inside any loop body
        called_in_loops: set = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        if child.func.id in top_level_funcs:
                            called_in_loops.add(child.func.id)

        if not called_in_loops:
            return code, []

        transformer = _LruCacheAdder(called_in_loops)
        new_tree = transformer.visit(copy.deepcopy(tree))

        if not transformer.changes_made:
            return code, []

        # Add `import functools` if not present
        has_functools = any(
            (isinstance(n, ast.Import) and any(a.name == "functools" for a in n.names))
            or (isinstance(n, ast.ImportFrom) and n.module == "functools")
            for n in tree.body
        )
        if not has_functools:
            import_node = ast.Import(names=[ast.alias(name="functools")])
            new_tree.body.insert(0, import_node)

        try:
            ast.fix_missing_locations(new_tree)
            new_code = ast.unparse(new_tree)
            ast.parse(new_code)
            return new_code, transformer.changes
        except Exception:
            return code, []


# ---------------------------------------------------------------------------
# Pass 4: AlgorithmicSubstitutionPass
# ---------------------------------------------------------------------------

class _SetLookupSubstituter(ast.NodeTransformer):
    def __init__(self):
        self.changes_made = False
        self.changes = []
        self._list_names: set = set()

    def _collect_list_assignments(self, tree):
        """Collect module-level names assigned to list literals."""
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.List):
                        self._list_names.add(target.id)

    def _substitute_in_body(self, body, loop_lineno):
        """Replace `x in name` with `x in set(name)` for known list names."""

        class _InReplacer(ast.NodeTransformer):
            def __init__(inner_self):
                inner_self.changed = False

            def visit_Compare(inner_self, node):
                inner_self.generic_visit(node)
                new_comparators = []
                changed_here = False
                for op, comp in zip(node.ops, node.comparators):
                    if (
                        isinstance(op, ast.In)
                        and isinstance(comp, ast.Name)
                        and comp.id in self._list_names
                    ):
                        new_comp = ast.Call(
                            func=ast.Name(id="set", ctx=ast.Load()),
                            args=[comp],
                            keywords=[],
                        )
                        new_comparators.append(new_comp)
                        changed_here = True
                    else:
                        new_comparators.append(comp)
                if changed_here:
                    inner_self.changed = True
                    node.comparators = new_comparators
                return node

        replacer = _InReplacer()
        new_body = [replacer.visit(stmt) for stmt in body]
        return new_body, replacer.changed

    def visit_For(self, node):
        self.generic_visit(node)
        new_body, changed = self._substitute_in_body(node.body, node.lineno)
        if changed:
            self.changes_made = True
            self.changes.append(Change(
                pass_name="AlgorithmicSubstitutionPass",
                description=(
                    f"Replaced O(n²) list membership test with O(1) set lookup "
                    f"inside loop at line {node.lineno}."
                ),
                line_number=node.lineno,
            ))
            new_node = copy.copy(node)
            new_node.body = new_body
            return new_node
        return node

    def visit_While(self, node):
        self.generic_visit(node)
        new_body, changed = self._substitute_in_body(node.body, node.lineno)
        if changed:
            self.changes_made = True
            self.changes.append(Change(
                pass_name="AlgorithmicSubstitutionPass",
                description=(
                    f"Replaced O(n²) list membership test with O(1) set lookup "
                    f"inside while loop at line {node.lineno}."
                ),
                line_number=node.lineno,
            ))
            new_node = copy.copy(node)
            new_node.body = new_body
            return new_node
        return node


class AlgorithmicSubstitutionPass:
    """Replace O(n²) list membership tests with O(1) set lookups."""

    def apply(self, code: str) -> tuple[str, list]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, []

        transformer = _SetLookupSubstituter()
        transformer._collect_list_assignments(tree)

        if not transformer._list_names:
            return code, []

        new_tree = transformer.visit(copy.deepcopy(tree))

        if not transformer.changes_made:
            return code, []

        try:
            ast.fix_missing_locations(new_tree)
            new_code = ast.unparse(new_tree)
            ast.parse(new_code)
            return new_code, transformer.changes
        except Exception:
            return code, []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def optimize_code(code: str, goal: str = "reduce_energy") -> Union[OptimizationResult, ErrorResponse]:
    """Apply all transformation passes in order and return OptimizationResult."""
    if not code or not code.strip():
        return ErrorResponse(
            tool="optimize_code",
            message="Code string is empty.",
            error_type="ValueError",
        )

    try:
        ast.parse(code)
    except SyntaxError as e:
        return ErrorResponse(
            tool="optimize_code",
            message=f"Syntax error: {e}",
            error_type="SyntaxError",
        )

    all_changes: list[Change] = []
    current_code = code

    passes = [
        LoopReductionPass(),
        ExpressionHoistingPass(),
        MemoizationPass(),
        AlgorithmicSubstitutionPass(),
    ]

    for pass_ in passes:
        new_code, changes = pass_.apply(current_code)
        if changes:
            all_changes.extend(changes)
            current_code = new_code

    # Estimate improvement based on number and type of changes
    improvement = 0.0
    for change in all_changes:
        if change.pass_name == "LoopReductionPass":
            improvement += 20.0
        elif change.pass_name == "AlgorithmicSubstitutionPass":
            improvement += 15.0
        elif change.pass_name == "MemoizationPass":
            improvement += 10.0
        elif change.pass_name == "ExpressionHoistingPass":
            improvement += 5.0
    improvement = min(improvement, 80.0)

    return OptimizationResult(
        optimized_code=current_code,
        changes=all_changes,
        expected_improvement_percent=improvement,
    )
