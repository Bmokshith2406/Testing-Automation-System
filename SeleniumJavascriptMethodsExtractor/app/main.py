from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import extract, health
from app.middleware.audit import AuditMiddleware
from app.core.logging import setup_logging
from app.core.config import get_settings

# -------------------------------------------------------
# Initialize logging ONCE at import-time
# This prevents duplicate handlers in reload loops.
# -------------------------------------------------------
settings = get_settings()
setup_logging(settings.LOG_LEVEL)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Selenium JavaScript Method Extractor",
        version=settings.VERSION,
        description=(
            "Extract high-fidelity JavaScript Selenium/WebDriver methods and functions "
            "using a structured AST (Tree-sitter) pipeline."
        ),
    )

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

    return app


# Application instance
app = create_app()
