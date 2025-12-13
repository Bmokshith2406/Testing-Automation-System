from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Any, Dict


def utc_timestamp() -> datetime:
    """
    Unified UTC timestamp generator for API logs and raw script storage.

    Returns a timezone-aware UTC datetime without microseconds,
    suitable for MongoDB storage and cross-service consistency.
    """
    return datetime.now(timezone.utc).replace(microsecond=0)


# -----------------------------------------
# API LOG MODEL
# -----------------------------------------
class APILog(BaseModel):
    """
    Stores metadata about API requests for the
    Playwright JavaScript method extraction pipeline.
    """

    timestamp: datetime = Field(default_factory=utc_timestamp)

    # Request info
    method: Optional[str] = None
    path: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None

    # Processing info
    duration_ms: Optional[float] = None
    status: Optional[int] = None

    # Extraction-related metadata
    file_name: Optional[str] = None
    method_count: Optional[int] = None
    chunk_count: Optional[int] = None

    # Errors
    storage_error: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None

    model_config = {
        "from_attributes": False
    }


# -----------------------------------------
# RAW SCRIPT STORAGE MODEL
# -----------------------------------------
class RawScript(BaseModel):
    """
    Stores raw uploaded Playwright JavaScript source code
    along with metadata for audit and debugging.
    """

    filename: str
    content: str
    size: int
    timestamp: datetime = Field(default_factory=utc_timestamp)

    model_config = {
        "from_attributes": False
    }
