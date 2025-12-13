from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import extract, extract_folder, health
from app.middleware.audit import AuditMiddleware
from app.core.logging import setup_logging, logger
from app.core.config import get_settings
from app.db.mongo import check_mongo_connection, close_mongo_connection

# -------------------------------------------------------
# Initialize logging ONCE at import-time
# This prevents duplicate handlers in reload loops.
# -------------------------------------------------------
settings = get_settings()
setup_logging(settings.LOG_LEVEL)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Playwright JavaScript Method Extractor",
        version=settings.VERSION,
        description=(
            "Extract high-fidelity Playwright JavaScript methods, page objects, "
            "and test logic using a structured AST (Tree-sitter) pipeline."
        ),
    )

    # -------------------------------------------------------
    # Startup / Shutdown events
    # -------------------------------------------------------
    @app.on_event("startup")
    async def startup_event():
        ok = await check_mongo_connection()
        if not ok:
            logger.warning(
                "MongoDB NOT connected at startup. "
                "Audit logs and raw script storage will not work."
            )

    @app.on_event("shutdown")
    async def shutdown_event():
        close_mongo_connection()

    # -------------------------------------------------------
    # CORS configuration
    # -------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # safe because allow_credentials=False
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------
    # Middleware
    # -------------------------------------------------------
    app.add_middleware(AuditMiddleware)

    # -------------------------------------------------------
    # Routes
    # -------------------------------------------------------
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(extract.router, prefix="/extract", tags=["Extraction"])
    app.include_router(
        extract_folder.router,
        prefix="/extract-folder",
        tags=["Extraction"],
    )

    return app


# -------------------------------------------------------
# Application instance
# -------------------------------------------------------
app = create_app()
