import io
import os
import zipfile
import tempfile
import time
import traceback
from datetime import datetime
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

from app.core.config import get_settings
from app.core.logging import logger
from app.core.utils import safe_decode
from app.db.mongo import log_api_call
from app.services.scanner import (
    parse_source,
    prepare_methods_with_inits,
    MethodInfo,
)
from app.services.validator import validate_methods, validate_chunk_order
from app.services.csv_writer import write_methods_to_csv


settings = get_settings()
router = APIRouter()

# --------------------------------------------------------------
# Directories to ignore during project traversal
# --------------------------------------------------------------
IGNORED_DIRS = {
    ".venv",
    "venv",
    ".git",
    "node_modules",
    "__pycache__",
}


@router.post(
    "/extract-project",
    summary="Extract methods from a Playwright Python project (ZIP upload)",
)
async def extract_project(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Accepts a ZIP file containing a Playwright Python project,
    recursively extracts all `.py` files, applies AST-based
    extraction, and returns a single CSV containing all methods.

    Safety limits and ignored folders are enforced.
    """

    start = time.perf_counter()
    timestamp = datetime.utcnow().replace(microsecond=0)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported for project extraction.",
        )

    zip_bytes = await file.read()

    # --------------------------------------------------------------
    # ZIP size limit
    # --------------------------------------------------------------
    if settings.MAX_ZIP_SIZE_MB > 0:
        max_zip_bytes = settings.MAX_ZIP_SIZE_MB * 1024 * 1024
        if len(zip_bytes) > max_zip_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"ZIP file exceeds maximum allowed size ({settings.MAX_ZIP_SIZE_MB} MB).",
            )

    all_methods: List[MethodInfo] = []
    python_file_count = 0
    total_file_count = 0
    extracted_size_bytes = 0

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "project.zip")

            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)

            # ------------------------------------------------------
            # Walk extracted project (ignore unwanted folders)
            # ------------------------------------------------------
            for root, dirs, files in os.walk(tmpdir):
                # Prevent os.walk from entering ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

                for fname in files:
                    total_file_count += 1

                    # --------------------------------------------------
                    # File count limit
                    # --------------------------------------------------
                    if settings.MAX_FILE_COUNT > 0 and total_file_count > settings.MAX_FILE_COUNT:
                        raise HTTPException(
                            status_code=400,
                            detail="Project contains too many files.",
                        )

                    file_path = os.path.join(root, fname)

                    # Track extracted size
                    try:
                        extracted_size_bytes += os.path.getsize(file_path)
                    except OSError:
                        continue

                    if settings.MAX_EXTRACTED_SIZE_MB > 0:
                        max_bytes = settings.MAX_EXTRACTED_SIZE_MB * 1024 * 1024
                        if extracted_size_bytes > max_bytes:
                            raise HTTPException(
                                status_code=400,
                                detail="Extracted project size exceeds allowed limit.",
                            )

                    # Only process Python files
                    if not fname.endswith(".py"):
                        continue

                    python_file_count += 1

                    # --------------------------------------------------
                    # Python file count limit
                    # --------------------------------------------------
                    if settings.MAX_PY_FILES > 0 and python_file_count > settings.MAX_PY_FILES:
                        raise HTTPException(
                            status_code=400,
                            detail="Too many Python files in project.",
                        )

                    try:
                        with open(file_path, "rb") as f:
                            source_text = safe_decode(f.read())

                        methods, init_map, global_map = parse_source(source_text)
                        prepared = prepare_methods_with_inits(
                            source_text,
                            methods,
                            init_map,
                            global_map,
                        )

                        validate_methods(prepared)
                        validate_chunk_order(prepared)

                        all_methods.extend(prepared)

                    except Exception as file_exc:
                        logger.error(
                            f"Failed processing file {file_path}: {file_exc}"
                        )

        if not all_methods:
            raise HTTPException(
                status_code=400,
                detail="No extractable Python methods found in project.",
            )

        csv_bytes = write_methods_to_csv(all_methods)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # ----------------------------------------------------------
        # Success log
        # ----------------------------------------------------------
        try:
            await log_api_call({
                "timestamp": timestamp,
                "ip": client_ip,
                "user_agent": user_agent,
                "file_name": file.filename,
                "method_count": len(all_methods),
                "chunk_count": None,
                "status": 200,
                "duration_ms": duration_ms,
                "python_file_count": python_file_count,
                "total_file_count": total_file_count,
            })
        except Exception as log_exc:
            logger.error(f"Logging error (project success): {log_exc}")

        download_name = f"project_methods_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.csv"

        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{download_name}"'
            },
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            f"Project extraction failed: {exc}\n{traceback.format_exc()}"
        )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        try:
            await log_api_call({
                "timestamp": timestamp,
                "ip": client_ip,
                "user_agent": user_agent,
                "file_name": file.filename,
                "method_count": 0,
                "chunk_count": 0,
                "status": 500,
                "duration_ms": duration_ms,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            })
        except Exception:
            pass

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error during project extraction."},
        )
