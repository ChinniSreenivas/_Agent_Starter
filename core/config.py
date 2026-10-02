"""
Configuration management using Pydantic Settings.
Loads from environment variables or .env file with production defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys & LLM Config
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 1.5
    REQUEST_TIMEOUT: float = 30.0

    # Application & Server Config
    APP_NAME: str = "GTM 4-Agent Real-Time Platform"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Human-In-The-Loop Configuration
    REQUIRE_APPROVAL_FOR_DISPATCH: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_gemini_configured(self) -> bool:
        """Checks if a valid Gemini API key is present."""
        return bool(
            self.GEMINI_API_KEY
            and self.GEMINI_API_KEY.strip()
            and self.GEMINI_API_KEY != "YOUR_API_KEY_HERE"
        )


settings = Settings()
