from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from datetime import datetime, timezone
import time
import traceback

from app.db.mongo import log_api_call
from app.core.logging import logger


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to audit and log all incoming API requests.

    Framework-agnostic, but used by the Playwright JavaScript
    method extraction pipeline.
    """

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        error_data = {}
        response = None

        try:
            # Proceed with the request
            response = await call_next(request)
            status_code = response.status_code

        except Exception as exc:
            # Handle unexpected server errors gracefully
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
            "timestamp": datetime.now(timezone.utc),
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
