from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Transaction Processing Pipeline"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_retries: int = 3

    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@db:5432/transactions"
    )
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    upload_dir: Path = Path("/app/uploads")
    max_upload_size_mb: int = 50


    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
