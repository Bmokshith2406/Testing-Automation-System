from typing import List, Dict, Any, Callable, Iterable, Iterator, Tuple, Protocol
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


class MethodInfoLike(Protocol):
    name: str
    start_line: int
    end_line: int
    code: str
    class_name: str
    is_nested: bool
    injected_vars: List[str]


@dataclass
class Chunk:
    index: int
    methods: List[MethodInfoLike]
    total_chars: int
    total_methods: int

    def __repr__(self):
        return f"Chunk(index={self.index}, total_methods={self.total_methods}, total_chars={self.total_chars})"


def _estimate_method_size(m: MethodInfoLike, buffer: int = 200) -> int:
    injected_len = sum(len(v) for v in (m.injected_vars or [])) + len(m.injected_vars)
    return len(m.code) + injected_len + buffer


def build_chunks(methods: List[MethodInfoLike], max_chars_per_chunk: int = 20000) -> List[Chunk]:
    chunks: List[Chunk] = []
    current: List[MethodInfoLike] = []
    current_chars = 0
    idx = 0

    # Ensure methods are sorted by start_line
    methods = sorted(methods, key=lambda m: m.start_line)

    for m in methods:
        m_size = _estimate_method_size(m)
        would_exceed = current_chars + m_size > max_chars_per_chunk

        if current and would_exceed:
            chunks.append(Chunk(index=idx, methods=current, total_chars=current_chars, total_methods=len(current)))
            idx += 1
            current = []
            current_chars = 0

        if not current and m_size > max_chars_per_chunk:
            chunks.append(Chunk(index=idx, methods=[m], total_chars=m_size, total_methods=1))
            idx += 1
            continue

        current.append(m)
        current_chars += m_size

    if current:
        chunks.append(Chunk(index=idx, methods=current, total_chars=current_chars, total_methods=len(current)))

    return chunks


def chunk_to_text(chunk: Chunk, separator: str = "\n\n") -> str:
    parts: List[str] = []
    for m in chunk.methods:
        if m.injected_vars:
            parts.extend(m.injected_vars)
        parts.append(m.code)
    return separator.join(parts).rstrip()


def iter_chunk_texts(methods: List[MethodInfoLike], max_chars_per_chunk: int = 20000) -> Iterator[Tuple[int, str]]:
    for c in build_chunks(methods, max_chars_per_chunk=max_chars_per_chunk):
        yield c.index, chunk_to_text(c)


def process_chunks_parallel(
    chunks: List[Chunk],
    worker_fn: Callable[[Chunk], Any],
    max_workers: int = 4,
    collect_results: bool = True
) -> List[Any]:
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
    return sum(_estimate_method_size(m) for m in methods)
