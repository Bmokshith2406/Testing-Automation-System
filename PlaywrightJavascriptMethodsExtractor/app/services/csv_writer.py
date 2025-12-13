import csv
import io
from typing import Iterable, List
from app.services.scanner import MethodInfo


def prevent_excel_injection(text: str) -> str:
    """
    Prevent Excel from interpreting Playwright JavaScript code lines
    as formulas when opening CSV files.
    """
    stripped = text.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def method_to_string(m: MethodInfo) -> str:
    """
    Convert a Playwright JavaScript method/function (with injected variables)
    into a normalized multiline text block.
    """
    parts: List[str] = []

    # Injected variables (globals, fixtures, constructor assignments, etc.)
    if m.injected_vars:
        for line in m.injected_vars:
            normalized = line.replace("\r\n", "\n").replace("\r", "\n")
            parts.append(normalized)
        parts.append("")  # Blank separator before method/function

    # Normalize Playwright JavaScript source code
    method_code = m.code.replace("\r\n", "\n").replace("\r", "\n")
    parts.append(method_code)

    final_block = "\n".join(parts).rstrip()

    # Secure each line against Excel CSV formula exploits
    safe_lines = [prevent_excel_injection(line) for line in final_block.split("\n")]
    return "\n".join(safe_lines)


def write_methods_to_csv(methods: List[MethodInfo]) -> bytes:
    """
    Write extracted Playwright JavaScript methods/functions into a CSV file.

    Output format:
    - Single column: "Raw Method"
    """
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    writer.writerow(["Raw Method"])

    for m in methods:
        writer.writerow([method_to_string(m)])

    return output.getvalue().encode("utf-8")


def iter_csv_rows(methods: List[MethodInfo]) -> Iterable[str]:
    """
    Generate CSV rows on-demand (streaming) for large
    Playwright JavaScript source files.
    """
    yield "Raw Method\n"

    for m in methods:
        block = method_to_string(m)
        block = block.replace("\n", "\\n")  # Escape newlines for streaming output
        yield block + "\n"
