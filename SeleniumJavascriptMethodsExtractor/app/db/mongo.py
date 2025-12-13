from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import APILog, RawScript


settings = get_settings()

# --------------------------------------------------------------
# MongoDB Client Initialization with Logging
# --------------------------------------------------------------
try:
    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=5000,  # fail fast
    )
    db = client[settings.MONGO_DB]
    logger.info("MongoDB client initialized")

except PyMongoError as e:
    logger.critical(f"MongoDB client initialization failed: {e}")
    raise


async def validate_mongo_connection() -> None:
    """
    Validate MongoDB connectivity using a ping command.
    Should be called once during application startup.
    """
    try:
        await client.admin.command("ping")
        logger.info(
            f"MongoDB connection established successfully "
            f"(db='{settings.MONGO_DB}')"
        )
    except Exception as e:
        logger.critical(f"MongoDB connection validation failed: {e}")
        raise


def now() -> datetime:
    """
    Return UTC timestamp for logs and raw script storage.
    Used for both JS and Python extractors.
    """
    return datetime.utcnow()


async def log_api_call(record: dict) -> None:
    """
    Insert API audit logs into MongoDB.
    All validation and DB write errors are swallowed safely
    to prevent logging failures from affecting API responses.
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
) -> None:
    """
    Store uploaded JavaScript Selenium script text (raw) for audit/debugging.
    Validated through RawScript Pydantic model.
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
