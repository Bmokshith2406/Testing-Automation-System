from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import APILog, RawScript

settings = get_settings()

# -------------------------------------------------------
# MongoDB client (shared across the application)
# -------------------------------------------------------
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]


def now():
    """
    Return UTC timestamp for logs and raw script storage.

    Used across the Playwright JavaScript extraction pipeline.
    """
    return datetime.now(timezone.utc)


# -------------------------------------------------------
# NEW: MongoDB connectivity check
# -------------------------------------------------------
async def check_mongo_connection() -> bool:
    """
    Verify MongoDB connectivity using a lightweight ping.

    Called during FastAPI startup to confirm Mongo availability.
    """
    try:
        await client.admin.command("ping")
        logger.info("MongoDB connection successful")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return False


async def log_api_call(record: dict):
    """
    Insert API audit logs into MongoDB.

    All validation and database write errors are safely swallowed
    to ensure logging failures do not affect API responses.
    """
    try:
        model = APILog(**record)
        await db[settings.COLLECTION_API_LOGS].insert_one(
            model.model_dump(mode="python")
        )
    except Exception as e:
        logger.error(f"MongoDB log_api_call failed: {e}")


async def store_raw_script(
    filename: str,
    content: str,
    metadata: dict | None = None,
):
    """
    Store uploaded Playwright JavaScript source code (raw) for audit/debugging.

    Content is validated using the RawScript Pydantic model
    before being persisted to MongoDB.
    """
    try:
        doc = {
            "filename": filename,
            "content": content,
            "size": len(content),
            "timestamp": now(),
        }

        if metadata:
            doc.update(metadata)

        model = RawScript(**doc)

        await db[settings.COLLECTION_RAW_SCRIPTS].insert_one(
            model.model_dump(mode="python")
        )

    except Exception as e:
        logger.error(f"MongoDB store_raw_script failed: {e}")


# -------------------------------------------------------
# OPTIONAL: clean shutdown helper
# -------------------------------------------------------
def close_mongo_connection():
    """
    Close MongoDB client on application shutdown.
    """
    try:
        client.close()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"MongoDB close failed: {e}")
