import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import logger
from app.db.mongo import ping_db, close_db
from app.services.embeddings import load_embedding_model, unload_embedding_model
from app.routes import auth, upload, search, admin, update


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

settings = get_settings()


# ------------------------------------------------------------------
# Lifespan manager
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    # --------------------------------------------------------------
    # Startup
    # --------------------------------------------------------------
    logger.info("Starting application lifespan...")

    # MongoDB
    try:
        await ping_db()
    except Exception as e:
        logger.error(
            f"MongoDB connection failed: {e}",
            exc_info=True,
        )

    # Embeddings    
    try:
        await load_embedding_model()
    except Exception as e:
        logger.error(
            f"Embedding model load failed: {e}",
            exc_info=True,
        )

    # Gemini
    if settings.GOOGLE_API_KEY:
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            logger.info("Gemini configured")
        except Exception as e:
            logger.error(
                f"Failed to configure Gemini: {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            "GOOGLE_API_KEY not set; Gemini features disabled."
        )

    yield

    # --------------------------------------------------------------
    # Shutdown
    # --------------------------------------------------------------
    try:
        await close_db()
    except Exception as e:
        logger.warning(
            f"Database shutdown encountered an issue: {e}"
        )

    try:
        await unload_embedding_model()
    except Exception as e:
        logger.warning(
            f"Embedding model unload encountered an issue: {e}"
        )

    logger.info("Lifespan shutdown complete")


# ------------------------------------------------------------------
# App initialization
# ------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)


# ------------------------------------------------------------------
# CORS Middleware
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(update.router, prefix="/api", tags=["Update"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])


# ------------------------------------------------------------------
# Root health endpoint (no templates / no frontend)
# ------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs"
    }
