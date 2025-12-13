from functools import cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar
import os


class Settings(BaseSettings):
    # --------------------------------------------------------------
    # Application Metadata
    # --------------------------------------------------------------
    APP_NAME: str = "Selenium Python Method Extractor (AST-Based)"
    VERSION: str = "1.0.0"
    CREATED_BY: str = "MOKSHITH BALIDI"

    # --------------------------------------------------------------
    # MongoDB Configuration
    # --------------------------------------------------------------
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB: str = "selenium_python_method_extractor"

    # --------------------------------------------------------------
    # Collections (now constants, not Pydantic fields)
    # --------------------------------------------------------------
    COLLECTION_RAW_SCRIPTS: ClassVar[str] = "raw_scripts"
    COLLECTION_API_LOGS: ClassVar[str] = "api_logs"

    # --------------------------------------------------------------
    # Extraction Settings
    # --------------------------------------------------------------
    MAX_CHARS_PER_CHUNK: int = 20000

    # --------------------------------------------------------------
    # Logging Configuration
    # --------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

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
