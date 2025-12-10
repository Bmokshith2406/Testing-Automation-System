from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

_mongo_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _mongo_client

    try:
        if _mongo_client is None:
            logger.info("Connecting to MongoDB Atlas...")

            try:
                _mongo_client = AsyncIOMotorClient(
                    settings.MONGO_CONNECTION_STRING,
                    serverSelectionTimeoutMS=5000,
                    tls=True,
                )
            except Exception as err:
                logger.exception(f"MongoDB client initialization failed: {err}")
                raise

        return _mongo_client

    except Exception:
        # Preserve baseline behavior: bubble up errors
        raise


def get_db() -> AsyncIOMotorDatabase:
    try:
        client = get_client()
        return client[settings.DB_NAME]
    except Exception:
        # Preserve baseline behavior: bubble up errors
        raise


async def ping_db():
    try:
        client = get_client()
    except Exception:
        raise

    try:
        await client.admin.command("ping")
        logger.info("MongoDB ping successful")
    except Exception as err:
        logger.exception(f"MongoDB ping failed: {err}")
        raise


async def close_db():
    global _mongo_client

    try:
        if _mongo_client is not None:
            try:
                _mongo_client.close()
            except Exception as err:
                logger.warning(f"MongoDB close encountered an error: {err}")

            logger.info("MongoDB connection closed")
            _mongo_client = None

    except Exception:
        pass


def get_testcase_collection():
    try:
        db = get_db()
        return db[settings.COLLECTION_TESTCASES]
    except Exception:
        raise


def get_users_collection():
    try:
        db = get_db()
        return db[settings.COLLECTION_USERS]
    except Exception:
        raise
