from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShvetVarni FastAPI Template"

    app_env: Literal[
        "development",
        "test",
        "staging",
        "production",
    ] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: SecretStr
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: int = Field(default=30, ge=1)

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "shvetvarni-fastapi-template"
    jwt_audience: str = "shvetvarni-api"

    access_token_minutes: int = 15
    refresh_token_days: int = 7

    redis_url: str = "redis://localhost:6379/0"

    # Celery configuration.
    # Keep the broker separate from the application's Redis DB.
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    celery_task_max_retries: int = Field(default=3, ge=0, le=10)
    celery_task_retry_delay_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
    )

    # Email configuration.
    email_provider: Literal["console", "smtp"] = "console"
    email_from: str = "sprajapat160599@gmail.com"

    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = True

    # The public frontend URL used to build verification links.
    email_verification_base_url: str = "http://localhost:3000"
    email_verification_token_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
    )

    cors_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()