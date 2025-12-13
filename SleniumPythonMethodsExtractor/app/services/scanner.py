from dataclasses import dataclass
import ast
from typing import List, Optional, Tuple, Dict


IGNORE_METHODS = {"main", "setup_driver"}


@dataclass
class MethodInfo:
    name: str
    start_line: int
    end_line: int
    code: str
    class_name: Optional[str]
    is_nested: bool
    injected_vars: List[str]


def _get_node_end_lineno(node: ast.AST) -> int:
    if hasattr(node, "end_lineno") and node.end_lineno:
        return node.end_lineno

    # Fallback: only inspect direct children, not full walk
    max_lineno = getattr(node, "lineno", 0)
    for child in ast.iter_child_nodes(node):
        child_end = getattr(child, "end_lineno", None)
        if child_end:
            max_lineno = max(max_lineno, child_end)
        elif hasattr(child, "lineno"):
            max_lineno = max(max_lineno, child.lineno)
    return max_lineno


def _slice_source_lines(source_lines: List[str], start_line: int, end_line: int) -> str:
    s = max(0, start_line - 1)
    e = min(len(source_lines), end_line)
    return "\n".join(source_lines[s:e])


def extract_init_assignments(tree: ast.AST) -> Dict[str, List[Tuple[str, int]]]:
    init_map: Dict[str, List[Tuple[str, int]]] = {}

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            attrs = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                    for stmt in item.body:
                        # self.x = ...
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                                    attrs.append((target.attr, stmt.lineno))
                        # self.x: Type = ...
                        elif isinstance(stmt, ast.AnnAssign):
                            t = stmt.target
                            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                                attrs.append((t.attr, stmt.lineno))
            if attrs:
                init_map[node.name] = attrs

    return init_map


def extract_global_assignments(source_lines: List[str], tree: ast.AST) -> Dict[str, str]:
    global_map = {}
    for node in tree.body:

        # x = value
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                line_idx = node.lineno - 1
                if 0 <= line_idx < len(source_lines):
                    global_map[node.targets[0].id] = source_lines[line_idx]

        # x: Type = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            line_idx = node.lineno - 1
            if 0 <= line_idx < len(source_lines):
                global_map[node.target.id] = source_lines[line_idx]

    return global_map


def parse_source(source: str) -> Tuple[List[MethodInfo], Dict[str, List[Tuple[str, int]]], Dict[str, str]]:
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    source_lines = source.splitlines()
    tree = ast.parse(source)

    methods: List[MethodInfo] = []
    init_map = extract_init_assignments(tree)
    global_map = extract_global_assignments(source_lines, tree)

    seen_methods = set()

    for node in tree.body:

        # module-level methods
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            if node.name not in IGNORE_METHODS:
                start, end = node.lineno, _get_node_end_lineno(node)
                code = _slice_source_lines(source_lines, start, end)

                methods.append(MethodInfo(node.name, start, end, code, None, False, []))
                seen_methods.add((start, end))

            # nested functions at module level
            for sub in ast.iter_child_nodes(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name not in IGNORE_METHODS:
                        s, e = sub.lineno, _get_node_end_lineno(sub)
                        if (s, e) not in seen_methods:
                            code = _slice_source_lines(source_lines, s, e)
                            methods.append(MethodInfo(sub.name, s, e, code, None, True, []))
                            seen_methods.add((s, e))

        # class-level methods
        elif isinstance(node, ast.ClassDef):
            class_name = node.name

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name != "__init__":
                    if item.name not in IGNORE_METHODS:
                        s, e = item.lineno, _get_node_end_lineno(item)
                        code = _slice_source_lines(source_lines, s, e)

                        methods.append(MethodInfo(item.name, s, e, code, class_name, False, []))
                        seen_methods.add((s, e))

                    # nested methods inside class
                    for sub in ast.iter_child_nodes(item):
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if sub.name not in IGNORE_METHODS:
                                s2, e2 = sub.lineno, _get_node_end_lineno(sub)
                                if (s2, e2) not in seen_methods:
                                    code2 = _slice_source_lines(source_lines, s2, e2)
                                    methods.append(MethodInfo(sub.name, s2, e2, code2, class_name, True, []))
                                    seen_methods.add((s2, e2))

    methods.sort(key=lambda m: m.start_line)
    return methods, init_map, global_map


def prepare_methods_with_inits(source: str, methods: List[MethodInfo], init_map, global_map):
    source_lines = source.splitlines()
    prepared = []
    global_lines = list(global_map.values())

    for m in methods:
        injected = list(global_lines)  # copy
        if injected:
            injected.append("")

        if m.class_name:
            for attr_name, lineno in init_map.get(m.class_name, []):
                idx = lineno - 1
                if 0 <= idx < len(source_lines):
                    injected.append(source_lines[idx])

        prepared.append(MethodInfo(
            m.name,
            m.start_line,
            m.end_line,
            m.code,
            m.class_name,
            m.is_nested,
            injected,
        ))

    return prepared
