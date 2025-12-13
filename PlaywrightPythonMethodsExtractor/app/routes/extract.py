import io
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import get_settings
from app.core.logging import logger
from app.core.utils import safe_decode
from app.db.mongo import log_api_call, store_raw_script
from app.services.chunker import build_chunks
from app.services.csv_writer import write_methods_to_csv
from app.services.scanner import parse_source, prepare_methods_with_inits
from app.services.validator import validate_chunk_order, validate_methods


settings = get_settings()
router = APIRouter()


@router.post(
    "/",
    summary="Extract methods from a Playwright Python script and return them as CSV",
)
async def extract_methods(
    request: Request,
    file: Optional[UploadFile] = File(None),
    script: Optional[str] = Form(None),
):
    """
    Accepts a Playwright Python script (file upload or pasted text),
    extracts all methods using AST parsing, and returns the result
    as a downloadable CSV file.
    """

    start = time.perf_counter()
    timestamp = datetime.utcnow().replace(microsecond=0)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # --------------------------------------------------------------
    # Input validation
    # --------------------------------------------------------------
    if not file and (not script or script.strip() == ""):
        raise HTTPException(
            status_code=400,
            detail="Provide either a file or a 'script' text field.",
        )

    try:
        # ----------------------------------------------------------
        # Load Playwright Python script
        # ----------------------------------------------------------
        if file:
            filename = file.filename or "uploaded_playwright_script.py"
            raw_bytes = await file.read()
            source_text = safe_decode(raw_bytes)
        else:
            filename = "pasted_playwright_script.py"
            source_text = script

        # ----------------------------------------------------------
        # Store raw script (best-effort, non-blocking)
        # ----------------------------------------------------------
        storage_error = None
        try:
            await store_raw_script(filename, source_text)
        except Exception as storage_exc:
            storage_error = str(storage_exc)

        # ----------------------------------------------------------
        # AST-based method extraction
        # ----------------------------------------------------------
        methods, init_map, global_map = parse_source(source_text)

        prepared_methods = prepare_methods_with_inits(
            source_text,
            methods,
            init_map,
            global_map,
        )

        validate_methods(prepared_methods)
        validate_chunk_order(prepared_methods)

        chunks = build_chunks(
            prepared_methods,
            max_chars_per_chunk=settings.MAX_CHARS_PER_CHUNK,
        )

        # ----------------------------------------------------------
        # CSV generation
        # ----------------------------------------------------------
        csv_bytes = write_methods_to_csv(prepared_methods)

        # ----------------------------------------------------------
        # Success audit log
        # ----------------------------------------------------------
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_record = {
            "timestamp": timestamp,
            "ip": client_ip,
            "user_agent": user_agent,
            "file_name": filename,
            "method_count": len(prepared_methods),
            "chunk_count": len(chunks),
            "status": 200,
            "duration_ms": duration_ms,
            "storage_error": storage_error,
        }

        try:
            await log_api_call(log_record)
        except Exception as log_exc:
            logger.error(f"Logging error (success case): {log_exc}")

        download_name = f"methods_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.csv"

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
            f"Playwright method extraction failed: {exc}\n{traceback.format_exc()}"
        )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        error_log = {
            "timestamp": timestamp,
            "ip": client_ip,
            "user_agent": user_agent,
            "file_name": filename if "filename" in locals() else None,
            "method_count": 0,
            "chunk_count": 0,
            "status": 500,
            "duration_ms": duration_ms,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

        try:
            await log_api_call(error_log)
        except Exception as log_exc:
            logger.error(f"Logging error (failure case): {log_exc}")

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error during extraction."},
        )
