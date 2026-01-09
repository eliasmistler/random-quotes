"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Ransom Notes API"
    debug: bool = False
    api_prefix: str = "/api"


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
