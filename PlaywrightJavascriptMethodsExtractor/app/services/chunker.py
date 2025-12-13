from typing import List, Dict, Any, Callable, Iterator, Tuple, Protocol
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


class MethodInfoLike(Protocol):
    """
    Protocol for extracted Playwright JavaScript method/function objects.

    The JavaScript scanner must return objects with:
    - name
    - start_line
    - end_line
    - code (full method/function source text)
    - class_name (or None for standalone functions)
    - is_nested
    - injected_vars (list of strings: global vars, constructor vars, fixtures, etc.)
    """
    name: str
    start_line: int
    end_line: int
    code: str
    class_name: str
    is_nested: bool
    injected_vars: List[str]


@dataclass
class Chunk:
    """
    Represents a group of Playwright JavaScript methods/functions.

    Used for batching, size-limiting, embedding, and downstream processing.
    """
    index: int
    methods: List[MethodInfoLike]
    total_chars: int
    total_methods: int

    def __repr__(self):
        return (
            f"Chunk(index={self.index}, "
            f"total_methods={self.total_methods}, "
            f"total_chars={self.total_chars})"
        )


def _estimate_method_size(m: MethodInfoLike, buffer: int = 200) -> int:
    """
    Rough approximation of a Playwright JavaScript method/function size.

    Includes:
    - method/function source code
    - injected variables (globals, fixtures, constructor assignments)
    - a small buffer for formatting and separators
    """
    injected_len = sum(len(v) for v in (m.injected_vars or [])) + len(m.injected_vars)
    return len(m.code) + injected_len + buffer


def build_chunks(
    methods: List[MethodInfoLike],
    max_chars_per_chunk: int = 20000
) -> List[Chunk]:
    """
    Build sequential chunks of Playwright JavaScript methods/functions
    such that each chunk does not exceed max_chars_per_chunk.

    Guarantees:
    - original file order is preserved
    - oversized individual methods are placed in their own chunk
    """
    chunks: List[Chunk] = []
    current: List[MethodInfoLike] = []
    current_chars = 0
    idx = 0

    methods = sorted(methods, key=lambda m: m.start_line)

    for m in methods:
        m_size = _estimate_method_size(m)
        would_exceed = current_chars + m_size > max_chars_per_chunk

        if current and would_exceed:
            chunks.append(
                Chunk(
                    index=idx,
                    methods=current,
                    total_chars=current_chars,
                    total_methods=len(current),
                )
            )
            idx += 1
            current = []
            current_chars = 0

        if not current and m_size > max_chars_per_chunk:
            chunks.append(
                Chunk(
                    index=idx,
                    methods=[m],
                    total_chars=m_size,
                    total_methods=1,
                )
            )
            idx += 1
            continue

        current.append(m)
        current_chars += m_size

    if current:
        chunks.append(
            Chunk(
                index=idx,
                methods=current,
                total_chars=current_chars,
                total_methods=len(current),
            )
        )

    return chunks


def chunk_to_text(chunk: Chunk, separator: str = "\n\n") -> str:
    """
    Convert a chunk of Playwright JavaScript methods into a merged text block.
    """
    parts: List[str] = []
    for m in chunk.methods:
        if m.injected_vars:
            parts.extend(m.injected_vars)
        parts.append(m.code)
    return separator.join(parts).rstrip()


def iter_chunk_texts(
    methods: List[MethodInfoLike],
    max_chars_per_chunk: int = 20000
) -> Iterator[Tuple[int, str]]:
    """
    Yield (chunk_index, chunk_text) pairs for downstream consumption.
    """
    for c in build_chunks(methods, max_chars_per_chunk=max_chars_per_chunk):
        yield c.index, chunk_to_text(c)


def process_chunks_parallel(
    chunks: List[Chunk],
    worker_fn: Callable[[Chunk], Any],
    max_workers: int = 4,
    collect_results: bool = True,
) -> List[Any]:
    """
    Parallel processing helper for chunk-level operations.

    Useful for large Playwright JavaScript codebases or
    multi-stage extraction / embedding pipelines.
    """
    results_by_index: Dict[int, Any] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(worker_fn, c): c.index for c in chunks}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                results_by_index[idx] = fut.result()
            except Exception as exc:
                results_by_index[idx] = exc

    if collect_results:
        return [results_by_index[i] for i in range(len(chunks))]
    return []


def approximate_total_size(methods: List[MethodInfoLike]) -> int:
    """
    Compute total estimated size of all extracted Playwright
    JavaScript methods/functions.
    """
    return sum(_estimate_method_size(m) for m in methods)
