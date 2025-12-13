from typing import List
from app.services.scanner import MethodInfo


class ValidationError(Exception):
    pass


def validate_methods(methods: List[MethodInfo]) -> None:
    """
    Validate extracted JavaScript methods/functions.

    Ensures:
    - Valid start/end line numbers
    - Code block is non-empty
    - First non-empty line resembles a JS function/method expression
    - injected_vars is a list of strings
    """

    JS_VALID_STARTS = (
        "function ",          # function foo() {}
        "async function ",    # async function foo() {}
        "class ",             # class Foo {}
        "const ", "let ", "var ",   # const x = () => {}
        "export ", "static ",
        "("                   # (() => {...})
    )

    for m in methods:

        # 1. Valid line numbers
        if not isinstance(m.start_line, int) or not isinstance(m.end_line, int):
            raise ValidationError(f"Invalid line numbers in '{m.name}'")

        if m.end_line < m.start_line:
            raise ValidationError(f"Invalid line range in '{m.name}'")

        # 2. Must contain code
        if not m.code or not isinstance(m.code, str):
            raise ValidationError(f"Empty or invalid code block for '{m.name}'")

        # 3. First executable line
        first_code_line = None
        for line in m.code.splitlines():
            stripped = line.strip()
            if stripped:
                first_code_line = stripped
                break

        if not first_code_line:
            raise ValidationError(f"Method '{m.name}' contains no executable content.")

        # JS validation: allow broad patterns because JS is flexible
        if not first_code_line.startswith(JS_VALID_STARTS):

            # class method syntax example: login() {
            if "(" in first_code_line and first_code_line.endswith("{"):
                pass

            # arrow functions
            elif "=>" in first_code_line:
                pass

            else:
                raise ValidationError(
                    f"Method '{m.name}' does not look like a valid JavaScript "
                    f"function/method definition. First line: {first_code_line}"
                )

        # 4. injected_vars must be list[str]
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
