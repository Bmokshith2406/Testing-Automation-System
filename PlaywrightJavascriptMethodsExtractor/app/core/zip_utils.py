import zipfile
from typing import Iterator, Tuple


IGNORE_DIRS = (
    "node_modules/",
    "dist/",
    "build/",
    "coverage/",
    ".git/",
    ".playwright/",
)


def iter_playwright_sources(zip_bytes: bytes) -> Iterator[Tuple[str, str]]:
    """
    Yield (filename, source_text) for each JS/TS file
    in a Playwright project ZIP.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for info in z.infolist():
            name = info.filename

            if info.is_dir():
                continue

            if any(name.startswith(d) for d in IGNORE_DIRS):
                continue

            if not name.endswith((".js", ".ts")):
                continue

            raw = z.read(info)
            try:
                source = raw.decode("utf-8")
            except UnicodeDecodeError:
                source = raw.decode("latin-1")

            yield name, source
