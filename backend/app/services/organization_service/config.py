from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "organization_service"
    SERVICE_PORT: int = 8004
    DEBUG: bool = True

    _project_root: Path = Path(__file__).resolve().parents[3]
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_project_root}/volunteer_plus.db"
    LOG_LEVEL: str = "INFO"

    USER_SERVICE_URL: str = "http://localhost:8008"
    EVENT_SERVICE_URL: str = "http://localhost:8003"

    NOTIFICATION_SERVICE_URL: str = Field(
        default="http://localhost:8006",
        description="URL notification-сервиса (этап 5.4)",
    )
    NOTIFICATION_TIMEOUT_SECONDS: float = 3.0

    SERVICE_API_KEY: str = Field(
        default="dev-insecure-service-key-change-in-production",
        description="Service-to-service API key (env: ORGANIZATION_SERVICE_API_KEY)",
    )

    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production",
        description="JWT secret key (env: ORGANIZATION_JWT_SECRET_KEY). "
        "Должен совпадать с USER_JWT_SECRET_KEY.",
    )
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="ORGANIZATION_",
    )

    @model_validator(mode="after")
    def validate_secrets_for_production(self):
        """Проверка, что секретные ключи заменены в production-режиме"""
        if not self.DEBUG:
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via ORGANIZATION_SERVICE_API_KEY environment variable in production"
                )
            if self.JWT_SECRET_KEY == "dev-insecure-secret-key-change-in-production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set via ORGANIZATION_JWT_SECRET_KEY environment variable in production"
                )
        return self

    @property
    def db_path(self) -> Path:
        return Path(self.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    db_path = Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
    if db_path.parent and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
