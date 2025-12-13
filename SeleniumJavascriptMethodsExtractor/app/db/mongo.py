from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import APILog, RawScript

settings = get_settings()

# MongoDB client (shared across the app)
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]


def now():
    """
    Return UTC timestamp for logs and raw script storage.
    Used for both JS and Python extractors.
    """
    return datetime.utcnow()


async def log_api_call(record: dict):
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


async def store_raw_script(filename: str, content: str, metadata: dict = None):
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
