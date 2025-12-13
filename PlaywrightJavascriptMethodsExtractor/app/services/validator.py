from typing import List
from app.services.scanner import MethodInfo


class ValidationError(Exception):
    pass


def validate_methods(methods: List[MethodInfo]) -> None:
    """
    Validate extracted Playwright JavaScript methods/functions.

    Ensures:
    - Valid start/end line numbers
    - Code block is non-empty
    - First non-empty line resembles a valid JS function/method
    - injected_vars is a list of strings
    """

    JS_VALID_STARTS = (
        "function ",           # function foo() {}
        "async function ",     # async function foo() {}
        "class ",              # class Foo {}
        "const ", "let ", "var ",  # const x = () => {}
        "export ",             # export function foo() {}
        "static ",             # static method() {}
        "test(",               # test('name', async () => {})
        "test.",               # test.describe(), test.only(), etc.
        "("                    # (() => {...})
    )

    for m in methods:

        # --------------------------------------------------
        # 1. Valid line numbers
        # --------------------------------------------------
        if not isinstance(m.start_line, int) or not isinstance(m.end_line, int):
            raise ValidationError(f"Invalid line numbers in '{m.name}'")

        if m.end_line < m.start_line:
            raise ValidationError(f"Invalid line range in '{m.name}'")

        # --------------------------------------------------
        # 2. Must contain code
        # --------------------------------------------------
        if not m.code or not isinstance(m.code, str):
            raise ValidationError(f"Empty or invalid code block for '{m.name}'")

        # --------------------------------------------------
        # 3. First executable line
        # --------------------------------------------------
        first_code_line = None
        for line in m.code.splitlines():
            stripped = line.strip()
            if stripped:
                first_code_line = stripped
                break

        if not first_code_line:
            raise ValidationError(
                f"Method '{m.name}' contains no executable content."
            )

        # --------------------------------------------------
        # 4. JavaScript / Playwright syntax validation
        # --------------------------------------------------
        if not first_code_line.startswith(JS_VALID_STARTS):

            # Class method syntax example: login() {
            if "(" in first_code_line and first_code_line.endswith("{"):
                pass

            # Arrow functions: const fn = () => {}
            elif "=>" in first_code_line:
                pass

            else:
                raise ValidationError(
                    f"Method '{m.name}' does not look like a valid "
                    f"Playwright JavaScript function/method definition. "
                    f"First line: {first_code_line}"
                )

        # --------------------------------------------------
        # 5. injected_vars must be list[str]
        # --------------------------------------------------
        if not isinstance(m.injected_vars, list):
            raise ValidationError(f"'injected_vars' must be a list in '{m.name}'")

        for line in m.injected_vars:
            if not isinstance(line, str):
                raise ValidationError(
                    f"Injected variable must be a string in '{m.name}'"
                )


def validate_chunk_order(methods: List[MethodInfo]) -> None:
    """
    Ensure extracted Playwright JavaScript methods are in source-code order.
    """
    last_start = -1
    for m in methods:
        if m.start_line < last_start:
            raise ValidationError(
                f"Methods out of order: '{m.name}' starts at {m.start_line}, "
                f"previous method started at {last_start}"
            )
        last_start = m.start_line
