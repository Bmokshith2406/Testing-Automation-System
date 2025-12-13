from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import APILog, RawScript


settings = get_settings()

# --------------------------------------------------------------
# MongoDB Client Initialization
# --------------------------------------------------------------
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]


def now() -> datetime:
    """
    Return current UTC timestamp.

    Used for auditing Playwright Python script uploads
    and API call logging.
    """
    return datetime.utcnow()


async def log_api_call(record: dict) -> None:
    """
    Persist API call metadata to MongoDB.

    Used to audit requests made to the Playwright Python
    Method Extraction service. Any validation or database
    errors are safely logged.
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
    Store uploaded Playwright Python script content for
    auditing, debugging, and traceability.

    The data is validated using Pydantic models before
    being persisted to MongoDB.
    """
    try:
        document = {
            "filename": filename,
            "content": content,
            "size": len(content),
            "timestamp": now(),
        }

        if metadata:
            document.update(metadata)

        model = RawScript(**document)
        await db[settings.COLLECTION_RAW_SCRIPTS].insert_one(
            model.model_dump(mode="python")
        )

    except Exception as e:
        logger.error(f"MongoDB store_raw_script failed: {e}")
