from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import io
import traceback
from datetime import datetime
import time

from app.core.config import get_settings
from app.core.utils import safe_decode

# JS scanner
from app.services.scanner import parse_source as parse_js_source
from app.services.scanner import prepare_methods_with_inits as prepare_js_methods_with_inits


from app.services.chunker import build_chunks
from app.services.csv_writer import write_methods_to_csv
from app.services.validator import validate_methods, validate_chunk_order
from app.db.mongo import store_raw_script, log_api_call
from app.core.logging import logger

settings = get_settings()
router = APIRouter()


@router.post("/")
async def extract_methods(
    request: Request,
    file: Optional[UploadFile] = File(None),
    script: Optional[str] = Form(None),
):
    start = time.perf_counter()
    timestamp = datetime.utcnow().replace(microsecond=0)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if not file and (not script or script.strip() == ""):
        raise HTTPException(
            status_code=400,
            detail="Provide either a file upload or a 'script' text field."
        )

    try:
        # Load JS source
        if file:
            filename = file.filename or "uploaded_script.js"
            raw = await file.read()
            source_text = safe_decode(raw)
        else:
            filename = "pasted_script.js"
            source_text = script

        # Store raw script
        storage_error = None
        try:
            await store_raw_script(filename, source_text)
        except Exception as e:
            storage_error = str(e)

        # JS AST extraction
        methods, init_map, global_map = parse_js_source(source_text)
        prepared_methods = prepare_js_methods_with_inits(
            source_text, methods, init_map, global_map
        )

        validate_methods(prepared_methods)
        validate_chunk_order(prepared_methods)

        chunks = build_chunks(
            prepared_methods,
            max_chars_per_chunk=settings.MAX_CHARS_PER_CHUNK
        )

        csv_bytes = write_methods_to_csv(prepared_methods)

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
            # script_language removed (field removed)
        }

        try:
            await log_api_call(log_record)
        except Exception as e:
            logger.error(f"Logging error (success case): {e}")

        download_name = f"js_methods_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.csv"

        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename=\"{download_name}\"'}
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Extraction error: {e}\n{traceback.format_exc()}")

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        err_log = {
            "timestamp": timestamp,
            "ip": client_ip,
            "user_agent": user_agent,
            "file_name": filename if "filename" in locals() else None,
            "method_count": 0,
            "chunk_count": 0,
            "status": 500,
            "duration_ms": duration_ms,
            "error": str(e),
            "traceback": traceback.format_exc(),
            # script_language removed
        }

        try:
            await log_api_call(err_log)
        except Exception as e2:
            logger.error(f"Logging error (failure case): {e2}")

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error during JS method extraction."}
        )
