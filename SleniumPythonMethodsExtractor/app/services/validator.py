from typing import List
from app.services.scanner import MethodInfo


class ValidationError(Exception):
    pass


def validate_methods(methods: List[MethodInfo]) -> None:

    for m in methods:

        if not isinstance(m.start_line, int) or not isinstance(m.end_line, int):
            raise ValidationError(f"Invalid line numbers in '{m.name}'")

        if m.end_line < m.start_line:
            raise ValidationError(f"Invalid line range in '{m.name}'")

        if not m.code or not isinstance(m.code, str):
            raise ValidationError(f"Empty or invalid code block for '{m.name}'")

        # Determine first non-decorator line
        first_code_line = None
        for line in m.code.splitlines():
            stripped = line.strip()
            if stripped:  # ignore blank lines
                if stripped.startswith("@"):
                    continue
                first_code_line = stripped
                break

        if not first_code_line or not first_code_line.startswith(("def ", "async def ")):
            raise ValidationError(
                f"Method '{m.name}' does not start with a valid function definition. "
                f"Decorators may be present, but the first non-decorator line must start with def/async def."
            )

        if not isinstance(m.injected_vars, list):
            raise ValidationError(f"'injected_vars' must be a list in '{m.name}'")

        for line in m.injected_vars:
            if not isinstance(line, str):
                raise ValidationError(f"Injected var must be a string in '{m.name}'")


def validate_chunk_order(methods: List[MethodInfo]) -> None:
    last_start = -1
    for m in methods:
        if m.start_line < last_start:
            raise ValidationError(
                f"Methods out of order: '{m.name}' starts at {m.start_line}, "
                f"previous method started at {last_start}"
            )
        last_start = m.start_line
