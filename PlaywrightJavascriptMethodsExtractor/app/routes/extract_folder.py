from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Iterator
import io
import zipfile
import time
import traceback
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.utils import safe_decode
from app.core.logging import logger

from app.services.scanner import parse_source, prepare_methods_with_inits
from app.services.validator import validate_methods, validate_chunk_order
from app.services.chunker import build_chunks
from app.services.csv_writer import write_methods_to_csv

from app.db.mongo import log_api_call

settings = get_settings()
router = APIRouter()


# ---------------------------------------------------------
# ZIP traversal rules
# ---------------------------------------------------------
IGNORE_DIR_PREFIXES = (
    "node_modules/",
    "dist/",
    "build/",
    "coverage/",
    ".git/",
    ".playwright/",
)

VALID_EXTENSIONS = (".js", ".ts")


def iter_playwright_sources(zip_bytes: bytes) -> Iterator[str]:
    """
    Iterate over valid Playwright JavaScript / TypeScript source files
    inside a ZIP archive with safety limits.
    """

    max_total_bytes = settings.MAX_ZIP_TOTAL_UNCOMPRESSED_MB * 1024 * 1024
    max_file_bytes = settings.MAX_SINGLE_FILE_MB * 1024 * 1024
    max_file_count = settings.MAX_ZIP_FILE_COUNT

    total_uncompressed = 0
    file_count = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():

            file_count += 1
            if file_count > max_file_count:
                raise HTTPException(
                    status_code=413,
                    detail="ZIP contains too many files",
                )

            if info.is_dir():
                continue

            name = info.filename

            if any(name.startswith(prefix) for prefix in IGNORE_DIR_PREFIXES):
                continue

            if not name.endswith(VALID_EXTENSIONS):
                continue

            if info.file_size > max_file_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large inside ZIP: {name}",
                )

            total_uncompressed += info.file_size
            if total_uncompressed > max_total_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="ZIP expands beyond allowed uncompressed size",
                )

            yield safe_decode(zf.read(info))


# ---------------------------------------------------------
# API: Extract from Playwright project ZIP
# ---------------------------------------------------------
@router.post(
    "/",
    summary="Extract Playwright JavaScript methods from a ZIP project",
)
async def extract_folder(
    request: Request,
    zip_file: UploadFile = File(...),
):
    start = time.perf_counter()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a ZIP archive",
        )

    if zip_file.size:
        max_zip_bytes = settings.MAX_ZIP_SIZE_MB * 1024 * 1024
        if zip_file.size > max_zip_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"ZIP file too large. Max allowed is {settings.MAX_ZIP_SIZE_MB} MB",
            )

    try:
        zip_bytes = await zip_file.read()
        all_methods = []

        # -------------------------------------------------
        # Per-file extraction (CORRECT)
        # -------------------------------------------------
        for source_text in iter_playwright_sources(zip_bytes):

            methods, init_map, global_map = parse_source(source_text)
            prepared = prepare_methods_with_inits(
                source_text,
                methods,
                init_map,
                global_map,
            )

            validate_methods(prepared)
            validate_chunk_order(prepared)  # ✅ per-file only

            all_methods.extend(prepared)

        if not all_methods:
            raise HTTPException(
                status_code=400,
                detail="No valid Playwright JavaScript/TypeScript files found in ZIP",
            )

        chunks = build_chunks(
            all_methods,
            max_chars_per_chunk=settings.MAX_CHARS_PER_CHUNK,
        )

        csv_bytes = write_methods_to_csv(all_methods)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        try:
            await log_api_call(
                {
                    "timestamp": timestamp,
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "method_count": len(all_methods),
                    "chunk_count": len(chunks),
                    "status": 200,
                    "duration_ms": duration_ms,
                }
            )
        except Exception as log_exc:
            logger.error(f"Audit logging failed: {log_exc}")

        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    'attachment; filename="playwright_project_methods.csv"'
                )
            },
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            f"extract-folder failed: {exc}\n{traceback.format_exc()}"
        )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        try:
            await log_api_call(
                {
                    "timestamp": timestamp,
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "method_count": 0,
                    "chunk_count": 0,
                    "status": 500,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        except Exception:
            pass

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error during Playwright project extraction"
            },
        )
