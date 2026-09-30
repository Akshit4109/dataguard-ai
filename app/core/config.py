"""Application configuration settings management."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    APP_NAME: str = Field(default="DataGuard AI", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    APP_ENV: str = Field(default="development", description="Environment (development, staging, production)")
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    API_V1_STR: str = Field(default="/api/v1", description="API route prefix for v1")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Database configuration (placeholder for future phases - no connection created in Phase 1)
    DATABASE_URL: str | None = Field(
        default=None,
        description="PostgreSQL connection string (reserved for future database phase)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
