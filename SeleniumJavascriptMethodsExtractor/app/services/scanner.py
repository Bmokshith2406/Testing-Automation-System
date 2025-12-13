"""
JavaScript scanner using Tree-sitter (NO BUILDING REQUIRED).
Compatible with:
- Python 3.10 / 3.11
- tree-sitter==0.25.x
- tree_sitter_languages==1.10.x
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

from tree_sitter import Parser
from tree_sitter_languages import get_language


# ------------------------------
# Load JavaScript grammar
# ------------------------------
LANGUAGE = get_language("javascript")

PARSER = Parser()
PARSER.set_language(LANGUAGE)


# ------------------------------
# Data class
# ------------------------------
@dataclass
class MethodInfo:
    name: str
    start_line: int
    end_line: int
    code: str
    class_name: Optional[str]
    is_nested: bool
    injected_vars: List[str]


IGNORE_METHODS = {
    "main",
    "wait",
    "logStep",
    "createXpath",
    "openPage",
    "clickById",
    "typeById",
    "findResults",
    "runWithRetry"
}


# ------------------------------
# Utils
# ------------------------------
def _normalize(src: str):
    return src.replace("\r\n", "\n").replace("\r", "\n")


def _slice(b: bytes, node):
    return b[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _line(pt):
    return pt[0] + 1


def _walk(node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _find(root, types):
    for n in _walk(root):
        if n.type in types:
            yield n


def _find_desc(node, types):
    for d in _walk(node):
        if d is not node and d.type in types:
            yield d


def _id(b: bytes, node):
    for c in node.children:
        if c.type in ("identifier", "property_identifier"):
            return _slice(b, c).strip()
    return None


# ------------------------------
# Parsing
# ------------------------------
def parse_source(source: str):
    source = _normalize(source)
    b = source.encode("utf-8")
    tree = PARSER.parse(b)
    root = tree.root_node
    lines = source.splitlines()

    global_map = {}
    init_map = {}
    methods = []
    seen = set()

    # ----- global variables -----
    for child in root.children:
        if child.type in ("lexical_declaration", "variable_declaration"):
            for d in child.children:
                if d.type == "variable_declarator":
                    name = _id(b, d)
                    if name:
                        ln = _line(d.start_point)
                        global_map[name] = lines[ln - 1]

    # ----- constructor variables -----
    for cls in _find(root, ("class_declaration", "class")):
        cname = _id(b, cls) or f"<anon@{_line(cls.start_point)}>"

        for body in cls.children:
            if body.type == "class_body":
                for m in body.children:
                    if m.type == "method_definition" and _id(b, m) == "constructor":
                        for d in _walk(m):
                            txt = _slice(b, d)
                            if "this." in txt and "=" in txt:
                                ln = _line(d.start_point)
                                init_map.setdefault(cname, []).append((ln, txt))

    # helper
    def add(name, node, cname, nested):
        s = _line(node.start_point)
        e = _line(node.end_point)
        key = (s, e, cname or "")
        if key in seen:
            return
        seen.add(key)
        methods.append(MethodInfo(name, s, e, _slice(b, node), cname, nested, []))

    # ----- functions -----
    for fn in _find(root, ("function_declaration",)):
        name = _id(b, fn) or f"<anon@{_line(fn.start_point)}>"
        if name not in IGNORE_METHODS:
            add(name, fn, None, False)

        for sub in _find_desc(fn, ("function_declaration",)):
            sname = _id(b, sub) or f"<anon@{_line(sub.start_point)}>"
            add(sname, sub, None, True)

    # ----- variable-assigned / arrow functions -----
    for decl in _find(root, ("lexical_declaration", "variable_declaration")):
        for d in decl.children:
            if d.type == "variable_declarator":
                name = _id(b, d)
                init = None
                for c in d.children:
                    if c.type in ("arrow_function", "function", "function_expression"):
                        init = c
                if name and init:
                    add(name, init, None, False)

                    for sub in _find_desc(init, ("arrow_function", "function", "function_expression")):
                        add(f"<anon@{_line(sub.start_point)}>", sub, None, True)

    # ----- class methods -----
    for cls in _find(root, ("class_declaration", "class")):
        cname = _id(b, cls) or f"<anon@{_line(cls.start_point)}>"

        for body in cls.children:
            if body.type == "class_body":
                for m in body.children:
                    name = _id(b, m)
                    if m.type == "method_definition" and name not in (None, "constructor") and name not in IGNORE_METHODS:
                        add(name, m, cname, False)

    methods.sort(key=lambda m: m.start_line)
    return methods, init_map, global_map


# ------------------------------
# Inject variables
# ------------------------------
def prepare_methods_with_inits(source, methods, init_map, global_map):
    source = _normalize(source)
    lines = source.splitlines()

    globals_list = []
    for name, txt in global_map.items():
        for i, ln in enumerate(lines, start=1):
            if ln.strip() == txt.strip():
                globals_list.append((i, txt))

    globals_list.sort(key=lambda x: x[0])

    out = []
    for m in methods:
        injected = []

        for ln, txt in globals_list:
            if ln < m.start_line:
                injected.append(txt)

        if m.class_name:
            for ln, txt in init_map.get(m.class_name, []):
                if ln < m.start_line:
                    injected.append(txt)

        out.append(MethodInfo(m.name, m.start_line, m.end_line, m.code, m.class_name, m.is_nested, injected))

    return out
