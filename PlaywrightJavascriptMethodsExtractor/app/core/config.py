from functools import cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar
import os


class Settings(BaseSettings):
    # --------------------------------------------------------------
    # Application Metadata
    # --------------------------------------------------------------
    # Updated to reflect Playwright JavaScript extraction
    APP_NAME: str = "Playwright JavaScript Method Extractor"
    VERSION: str = "1.0.0"
    CREATED_BY: str = "MOKSHITH BALIDI"

    # --------------------------------------------------------------
    # MongoDB Configuration
    # --------------------------------------------------------------
    MONGO_URI: str = os.getenv("MONGO_URI", "")

    # Updated DB name for framework clarity
    MONGO_DB: str = "playwright_js_method_extractor"

    # --------------------------------------------------------------
    # Collections (constants; not treated as Pydantic fields)
    # --------------------------------------------------------------
    COLLECTION_RAW_SCRIPTS: ClassVar[str] = "raw_scripts"
    COLLECTION_API_LOGS: ClassVar[str] = "api_logs"

    # --------------------------------------------------------------
    # Extraction Settings
    # (Applies to Playwright JS method blocks)
    # --------------------------------------------------------------
    MAX_CHARS_PER_CHUNK: int = 20000

    # --------------------------------------------------------------
    # Logging Configuration
    # --------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    
    # ZIP ingestion limits
    MAX_ZIP_SIZE_MB: int = 50
    MAX_ZIP_TOTAL_UNCOMPRESSED_MB: int = 200
    MAX_ZIP_FILE_COUNT: int = 5000
    MAX_SINGLE_FILE_MB: int = 8


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
    return Settings()
