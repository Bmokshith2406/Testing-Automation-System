import time
from functools import wraps
from typing import Callable, Any, List, Iterable
from itertools import chain


def measure_time(func: Callable) -> Callable:
    """
    Decorator to measure execution time of any function.

    Used across the Playwright JavaScript extraction pipeline
    (JS scanner, chunker, CSV writer, validators).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        wrapper.last_duration_ms = round((time.perf_counter() - start) * 1000, 2)
        return result

    wrapper.last_duration_ms = None
    return wrapper


def safe_decode(raw_bytes: bytes) -> str:
    """
    Safely decode uploaded JavaScript source files.

    Playwright automation scripts may contain UTF-8 or legacy encodings,
    especially when sourced from older repositories.
    """
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


def flatten(list_of_lists: Iterable[Iterable[Any]]) -> List[Any]:
    """
    Flatten nested lists.

    Used when combining extracted Playwright JavaScript method blocks
    from multiple AST passes.
    """
    return list(chain.from_iterable(list_of_lists))
