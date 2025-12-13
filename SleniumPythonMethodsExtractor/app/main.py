from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import extract, health
from app.middleware.audit import AuditMiddleware
from app.core.logging import setup_logging, logger
from app.core.config import get_settings

# Mongo lifecycle helpers
from app.db.mongo import validate_mongo_connection, client


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Selenium Python Method Extractor (AST Only)",
        version=settings.VERSION,
        description="Extract byte-perfect Python Selenium methods using a safe AST pipeline.",
    )

    # -------------------------------------------------------
    # Application Lifecycle Events
    # -------------------------------------------------------
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Application startup initiated")
        await validate_mongo_connection()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Application shutdown initiated")
        client.close()
        logger.info("MongoDB client connection closed")

    # -------------------------------------------------------
    # CORS
    # -------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # only valid if allow_credentials=False
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

    logger.info("FastAPI application created successfully")
    return app


app = create_app()
