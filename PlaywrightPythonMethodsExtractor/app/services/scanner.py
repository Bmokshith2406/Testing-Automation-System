from dataclasses import dataclass
import ast
from typing import List, Optional, Tuple, Dict


# Methods that are framework / infrastructure / boilerplate
# and add little to no semantic value across Playwright projects
IGNORE_METHODS = {
    # ---------------------------------------------------------
    # Application / runner entry points
    # ---------------------------------------------------------
    "main",

    # ---------------------------------------------------------
    # Browser & context bootstrap (Playwright)
    # ---------------------------------------------------------
    "setup_browser",
    "create_browser",
    "create_context",
    "launch_browser",
    "new_context",
    "new_page",

    # ---------------------------------------------------------
    # BasePage-style thin wrappers (very common boilerplate)
    # ---------------------------------------------------------
    "goto",
    "open",
    "navigate",
    "get_title",
    "get_url",

    # ---------------------------------------------------------
    # Legacy Selenium leftovers (safe to keep for backward compat)
    # ---------------------------------------------------------
    "setup_driver",
}



@dataclass
class MethodInfo:
    """
    Represents a single extracted Python method or function.

    Used by the Playwright Python Method Extraction pipeline.
    """
    name: str
    start_line: int
    end_line: int
    code: str
    class_name: Optional[str]
    is_nested: bool
    injected_vars: List[str]


# ---------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------
def _get_node_end_lineno(node: ast.AST) -> int:
    """
    Safely determine the end line number of an AST node.

    Uses `end_lineno` when available (Python 3.8+),
    otherwise falls back to inspecting direct children.
    """
    if hasattr(node, "end_lineno") and node.end_lineno:
        return node.end_lineno

    max_lineno = getattr(node, "lineno", 0)
    for child in ast.iter_child_nodes(node):
        child_end = getattr(child, "end_lineno", None)
        if child_end:
            max_lineno = max(max_lineno, child_end)
        elif hasattr(child, "lineno"):
            max_lineno = max(max_lineno, child.lineno)

    return max_lineno


def _slice_source_lines(
    source_lines: List[str],
    start_line: int,
    end_line: int,
) -> str:
    """
    Extract source code between two line numbers (inclusive).
    """
    start = max(0, start_line - 1)
    end = min(len(source_lines), end_line)
    return "\n".join(source_lines[start:end])


# ---------------------------------------------------------
# Playwright-relevant context extraction
# ---------------------------------------------------------
def extract_init_assignments(
    tree: ast.AST,
) -> Dict[str, List[Tuple[str, int]]]:
    """
    Extract `self.<attr> = ...` assignments from class __init__ methods.

    These are injected before class methods to preserve
    execution context (important for Playwright page objects).
    """
    init_map: Dict[str, List[Tuple[str, int]]] = {}

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        attrs: List[Tuple[str, int]] = []

        for item in node.body:
            if (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "__init__"
            ):
                for stmt in item.body:
                    # self.x = ...
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                attrs.append((target.attr, stmt.lineno))

                    # self.x: Type = ...
                    elif isinstance(stmt, ast.AnnAssign):
                        t = stmt.target
                        if (
                            isinstance(t, ast.Attribute)
                            and isinstance(t.value, ast.Name)
                            and t.value.id == "self"
                        ):
                            attrs.append((t.attr, stmt.lineno))

        if attrs:
            init_map[node.name] = attrs

    return init_map


def extract_global_assignments(
    source_lines: List[str],
    tree: ast.AST,
) -> Dict[str, str]:
    """
    Extract top-level global variable assignments.

    These are injected before every extracted method,
    which is useful for Playwright fixtures, constants,
    and shared selectors.
    """
    global_map: Dict[str, str] = {}

    for node in tree.body:

        # x = value
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                idx = node.lineno - 1
                if 0 <= idx < len(source_lines):
                    global_map[node.targets[0].id] = source_lines[idx]

        # x: Type = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            idx = node.lineno - 1
            if 0 <= idx < len(source_lines):
                global_map[node.target.id] = source_lines[idx]

    return global_map


# ---------------------------------------------------------
# Core AST extraction
# ---------------------------------------------------------
def parse_source(
    source: str,
) -> Tuple[
    List[MethodInfo],
    Dict[str, List[Tuple[str, int]]],
    Dict[str, str],
]:
    """
    Parse Python source code and extract all functions and methods.

    Supports:
    - sync and async functions
    - class methods
    - nested functions
    - Playwright-style async tests
    """
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    source_lines = source.splitlines()
    tree = ast.parse(source)

    methods: List[MethodInfo] = []
    init_map = extract_init_assignments(tree)
    global_map = extract_global_assignments(source_lines, tree)

    seen_ranges = set()

    for node in tree.body:

        # ----------------------------
        # Module-level functions
        # ----------------------------
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name not in IGNORE_METHODS:
                s, e = node.lineno, _get_node_end_lineno(node)
                code = _slice_source_lines(source_lines, s, e)

                methods.append(
                    MethodInfo(node.name, s, e, code, None, False, [])
                )
                seen_ranges.add((s, e))

            # Nested functions
            for sub in ast.iter_child_nodes(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name not in IGNORE_METHODS:
                        s2, e2 = sub.lineno, _get_node_end_lineno(sub)
                        if (s2, e2) not in seen_ranges:
                            code2 = _slice_source_lines(source_lines, s2, e2)
                            methods.append(
                                MethodInfo(sub.name, s2, e2, code2, None, True, [])
                            )
                            seen_ranges.add((s2, e2))

        # ----------------------------
        # Class-level methods
        # ----------------------------
        elif isinstance(node, ast.ClassDef):
            class_name = node.name

            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name != "__init__"
                ):
                    if item.name not in IGNORE_METHODS:
                        s, e = item.lineno, _get_node_end_lineno(item)
                        code = _slice_source_lines(source_lines, s, e)

                        methods.append(
                            MethodInfo(item.name, s, e, code, class_name, False, [])
                        )
                        seen_ranges.add((s, e))

                    # Nested functions inside class methods
                    for sub in ast.iter_child_nodes(item):
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if sub.name not in IGNORE_METHODS:
                                s2, e2 = sub.lineno, _get_node_end_lineno(sub)
                                if (s2, e2) not in seen_ranges:
                                    code2 = _slice_source_lines(source_lines, s2, e2)
                                    methods.append(
                                        MethodInfo(
                                            sub.name,
                                            s2,
                                            e2,
                                            code2,
                                            class_name,
                                            True,
                                            [],
                                        )
                                    )
                                    seen_ranges.add((s2, e2))

    methods.sort(key=lambda m: m.start_line)
    return methods, init_map, global_map


# ---------------------------------------------------------
# Context injection
# ---------------------------------------------------------
def prepare_methods_with_inits(
    source: str,
    methods: List[MethodInfo],
    init_map: Dict[str, List[Tuple[str, int]]],
    global_map: Dict[str, str],
) -> List[MethodInfo]:
    """
    Inject global variables and __init__ assignments
    before each extracted method.
    """
    source_lines = source.splitlines()
    prepared: List[MethodInfo] = []

    global_lines = list(global_map.values())

    for m in methods:
        injected: List[str] = list(global_lines)

        if injected:
            injected.append("")

        if m.class_name:
            for _, lineno in init_map.get(m.class_name, []):
                idx = lineno - 1
                if 0 <= idx < len(source_lines):
                    injected.append(source_lines[idx])

        prepared.append(
            MethodInfo(
                m.name,
                m.start_line,
                m.end_line,
                m.code,
                m.class_name,
                m.is_nested,
                injected,
            )
        )

    return prepared
