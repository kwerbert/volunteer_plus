from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "feed_service"
    SERVICE_PORT: int = 8001
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/volunteer_plus"
    LOG_LEVEL: str = "INFO"
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300
    DEFAULT_SEARCH_RADIUS_KM: int = 10
    # URLs других микросервисов
    USER_SERVICE_URL: str = "http://localhost:8008"
    SUBSCRIPTION_SERVICE_URL: str = "http://localhost:8002"
    EVENT_SERVICE_URL: str = "http://localhost:8003"
    ORGANIZATION_SERVICE_URL: str = "http://localhost:8004"
    ANALYTICS_SERVICE_URL: str = "http://localhost:8005"
    # 🔐 Service-to-Service auth — загружается из переменных окружения
    SERVICE_API_KEY: str = Field(
        default="dev-insecure-service-key-change-in-production",
        description="Service-to-service API key (env: FEED_SERVICE_API_KEY)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="FEED_",
    )

    @model_validator(mode="after")
    def validate_secrets_for_production(self):
        """Проверка, что секретные ключи заменены в production-режиме"""
        if not self.DEBUG:
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via FEED_SERVICE_API_KEY environment variable in production"
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
