from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import extract, health, extract_project
from app.middleware.audit import AuditMiddleware
from app.core.logging import setup_logging, logger
from app.core.config import get_settings

# Mongo connection validator
from app.db.mongo import validate_mongo_connection, client


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Playwright Python Method Extractor (AST-Based)",
        version=settings.VERSION,
        description=(
            "Extract byte-perfect Python Playwright methods using a "
            "safe, deterministic AST-based extraction pipeline."
        ),
    )

    # --------------------------------------------------------------
    # Application Lifecycle Events
    # --------------------------------------------------------------
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Application startup initiated")
        await validate_mongo_connection()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Application shutdown initiated")
        client.close()
        logger.info("MongoDB client connection closed")

    # --------------------------------------------------------------
    # CORS Configuration
    # --------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # valid only when allow_credentials=False
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------------
    # Audit & Logging Middleware
    # --------------------------------------------------------------
    app.add_middleware(AuditMiddleware)

    # --------------------------------------------------------------
    # API Routes
    # --------------------------------------------------------------
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(extract.router, prefix="/extract", tags=["Extraction"])
    app.include_router(
        extract_project.router,
        prefix="/extract-project",
        tags=["Project Extraction"],
    )

    logger.info("FastAPI application created successfully")
    return app


app = create_app()
