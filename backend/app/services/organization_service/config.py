from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "organization_service"
    SERVICE_PORT: int = 8004
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/volunteer_plus"
    LOG_LEVEL: str = "INFO"
    USER_SERVICE_URL: str = "http://localhost:8008"
    EVENT_SERVICE_URL: str = "http://localhost:8003"
    NOTIFICATION_SERVICE_URL: str = Field(
        default="http://localhost:8006",
        description="URL notification-сервиса",
    )
    NOTIFICATION_TIMEOUT_SECONDS: float = 3.0
    CHAT_SERVICE_URL: str = Field(
        default="http://localhost:8007",
        description="URL chat-сервиса (синхронизация чатов)",
    )
    CHAT_TIMEOUT_SECONDS: float = 5.0
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
