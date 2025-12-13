from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any, Dict


def utc_timestamp() -> datetime:
    """
    Unified timestamp generator used for API logs and raw script storage.
    """
    return datetime.utcnow().replace(microsecond=0)


# -----------------------------------------
# API LOG MODEL
# -----------------------------------------
class APILog(BaseModel):
    """
    Stores metadata about API requests for both Python and JavaScript
    Selenium extraction pipelines.
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
    Stores raw uploaded script content (JavaScript or Python)
    along with metadata for audit/debugging.
    """

    filename: str
    content: str
    size: int
    timestamp: datetime = Field(default_factory=utc_timestamp)

    model_config = {
        "from_attributes": False
    }
