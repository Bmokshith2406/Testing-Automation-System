import csv
import io
from typing import Iterable, List
from app.services.scanner import MethodInfo


def prevent_excel_injection(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def method_to_string(m: MethodInfo) -> str:
    parts: List[str] = []

    # Injected vars
    if m.injected_vars:
        for line in m.injected_vars:
            norm = line.replace("\r\n", "\n").replace("\r", "\n")
            parts.append(norm)
        parts.append("")

    # Normalize method code
    method_code = m.code.replace("\r\n", "\n").replace("\r", "\n")
    parts.append(method_code)

    final_block = "\n".join(parts).rstrip()

    # Protect EACH line against Excel injection
    safe_lines = [prevent_excel_injection(line) for line in final_block.split("\n")]
    return "\n".join(safe_lines)


def write_methods_to_csv(methods: List[MethodInfo]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    writer.writerow(["Raw Method"])

    for m in methods:
        writer.writerow([method_to_string(m)])

    return output.getvalue().encode("utf-8")


def iter_csv_rows(methods: List[MethodInfo]) -> Iterable[str]:
    yield "Raw Method\n"
    for m in methods:
        block = method_to_string(m)
        block = block.replace("\n", "\\n") 
        yield block + "\n"
