from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import extract, health
from app.middleware.audit import AuditMiddleware
from app.core.logging import setup_logging
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Selenium Python Method Extractor (AST Only)",
        version=settings.VERSION,
        description="Extract byte-perfect Python Selenium methods using a safe AST pipeline.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # only valid if allow_credentials=False
        allow_credentials=False,    # fix wildcard + credentials mismatch
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(AuditMiddleware)

    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(extract.router, prefix="/extract", tags=["Extraction"])

    return app


app = create_app()
