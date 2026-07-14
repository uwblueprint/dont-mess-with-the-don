import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # Environment
    app_env: str = Field(default="development")

    # Database
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="password")
    postgres_db_dev: str = Field(default="dmwtd")
    postgres_db_test: str = Field(default="dmwtd_test")
    db_host: str = Field(default="localhost")
    database_url: str = Field(default="")

    # CORS
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # Server
    port: int = Field(default=8080)
    host: str = Field(default="0.0.0.0")

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


def get_settings() -> Settings:
    """Get settings based on environment"""
    environment = os.getenv("APP_ENV", "development")

    class EnvironmentSettings(Settings):
        app_env: str = environment

    return EnvironmentSettings()


# Global settings instance
settings = get_settings()


# Scheduler
scheduler_timezone: str = Field(default="America/New_York")