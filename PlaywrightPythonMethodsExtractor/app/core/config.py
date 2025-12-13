from functools import cache
from typing import ClassVar
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --------------------------------------------------------------
    # Application Metadata
    # --------------------------------------------------------------
    APP_NAME: str = "Playwright Python Method Extractor (AST-Based)"
    VERSION: str = "1.0.0"
    CREATED_BY: str = "MOKSHITH BALIDI"

    # --------------------------------------------------------------
    # MongoDB Configuration
    # --------------------------------------------------------------
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB: str = "playwright_python_method_extractor"

    # --------------------------------------------------------------
    # Collections (constants, not Pydantic fields)
    # --------------------------------------------------------------
    COLLECTION_RAW_SCRIPTS: ClassVar[str] = "raw_scripts"
    COLLECTION_API_LOGS: ClassVar[str] = "api_logs"

    # --------------------------------------------------------------
    # Extraction Settings
    # --------------------------------------------------------------
    MAX_CHARS_PER_CHUNK: int = 20_000

    # --------------------------------------------------------------
    # Logging Configuration
    # --------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # --------------------------------------------------------------
    # Project Extraction Safety Limits
    # --------------------------------------------------------------
    MAX_ZIP_SIZE_MB: int = 500          
    MAX_EXTRACTED_SIZE_MB: int = 2000    
    MAX_FILE_COUNT: int = 50000          
    MAX_PY_FILES: int = 10000            

    # --------------------------------------------------------------
    # Pydantic Settings (Pydantic v2)
    # --------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using functools.cache ensures that settings are loaded
    only once during the application lifecycle.
    """
    return Settings()
