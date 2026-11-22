from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "analytics_service"
    SERVICE_PORT: int = 8005
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/volunteer_plus"
    LOG_LEVEL: str = "INFO"
    EVENT_SERVICE_URL: str = "http://localhost:8003"
    ORGANIZATION_SERVICE_URL: str = "http://localhost:8004"
    USER_SERVICE_URL: str = "http://localhost:8008"
    SUBSCRIPTION_SERVICE_URL: str = "http://localhost:8002"
    DEFAULT_EVENT_HOURS: float = 4.0
    MIN_HOURS_FOR_PREFERRED_ROLE: float = 10.0
    # 🔐 Service-to-Service auth — загружается из переменных окружения
    SERVICE_API_KEY: str = Field(
        default="dev-insecure-service-key-change-in-production",
        description="Service-to-service API key (env: ANALYTICS_SERVICE_API_KEY)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="ANALYTICS_",
    )

    @model_validator(mode="after")
    def validate_secrets_for_production(self):
        """Проверка, что секретные ключи заменены в production-режиме"""
        if not self.DEBUG:
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via ANALYTICS_SERVICE_API_KEY environment variable in production"
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
