from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The provided ai/ package reads provider credentials with os.getenv().
# Load the project's local .env once so both its providers and Settings see
# the same configuration. Existing shell variables keep precedence.
load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FoodLens AI"
    app_env: str = "development"
    log_level: str = "INFO"
    offline_mode: bool = False
    database_url: str | None = None
    upload_dir: str = "uploads"
    max_upload_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)
    cache_ttl_seconds: int = Field(default=86_400, ge=1)
    max_concurrency: int = Field(default=10, ge=1, le=50)
    retry_attempts: int = Field(default=5, ge=1, le=8)
    retry_base_delay: float = Field(default=1.0, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
