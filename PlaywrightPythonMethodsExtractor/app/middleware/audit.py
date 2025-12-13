import time
import traceback
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.logging import logger
from app.db.mongo import log_api_call


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to audit all API requests.

    Captures request/response metadata, execution time,
    and error details for the Playwright Python Method
    Extraction service.
    """

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        error_data = {}
        response = None

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as exc:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
            error_data = {
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

            response = JSONResponse(
                {"detail": "Internal Server Error"},
                status_code=status_code,
            )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        record = {
            "timestamp": datetime.utcnow(),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "duration_ms": duration_ms,
            "status": status_code,
            **error_data,
        }

        try:
            await log_api_call(record)
        except Exception as log_exc:
            logger.error(f"Failed to write API log: {log_exc}")

        return response
