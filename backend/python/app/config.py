import os
from datetime import datetime

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

    # Frontend base URL, used to build links that point at the frontend
    # (e.g. event check-in links)
    frontend_url: str = Field(default="http://localhost:3000")

    # Event check-in opens this many minutes before an event starts, and closes when it ends
    check_in_opens_minutes_before: int = Field(default=15)

    # Strikes
    # A no-show strike is given this long after an event ends with no check-in
    strike_no_show_grace_minutes: int = Field(default=60)
    # Cancelling less than this many hours before an event's start gives a strike
    strike_late_cancellation_hours: int = Field(default=48)
    # Strikes expire this many months after the event's start
    strike_expiry_months: int = Field(default=6)
    # Only events ending at or after this time can give no-show strikes. Unset means none do,
    # since attendance wasn't recorded before check-in existed.
    strike_no_show_start: datetime | None = Field(default=None)

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"

    # Scheduler
    scheduler_timezone: str = Field(default="America/Toronto")
    event_generation_horizon_days: int = Field(default=90, ge=1)

    # Firebase Auth: the only thing needed to check ID tokens (no service-account key)
    firebase_project_id: str = Field(default="")

    # Object storage (Cloudflare R2)
    r2_access_key_id: str = Field(default="")
    r2_secret_access_key: str = Field(default="")
    r2_public_bucket_name: str = Field(default="")
    r2_private_bucket_name: str = Field(default="")
    r2_public_base_url: str = Field(default="")
    r2_key_prefix: str = Field(default="")
    r2_endpoint_url: str = Field(default="")
    # Signed URL lifetimes (seconds)
    signed_url_ttl_media_seconds: int = Field(default=3600)
    signed_url_ttl_waiver_signed_seconds: int = Field(default=300)


def get_settings() -> Settings:
    """Get settings based on environment"""
    environment = os.getenv("APP_ENV", "development")

    class EnvironmentSettings(Settings):
        app_env: str = environment

    return EnvironmentSettings()


# Global settings instance
settings = get_settings()
