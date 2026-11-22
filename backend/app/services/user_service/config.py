from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "user_service"
    SERVICE_PORT: int = 8008
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/volunteer_plus"

    # Ключи безопасности — загружаются из переменных окружения с USER_ префиксом
    # В production переменные должны быть установлены явно, fallback-значения только для DEV
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production",
        description="JWT secret key (env: USER_JWT_SECRET_KEY)",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_HASH_COST: int = 12
    SERVICE_API_KEY: str = Field(
        default="dev-insecure-service-key-change-in-production",
        description="Service-to-service API key (env: USER_SERVICE_API_KEY)",
    )
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://10.0.2.2:3000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="USER_",
    )

    @model_validator(mode="after")
    def validate_secrets_for_production(self):
        """Проверка, что секретные ключи заменены в production-режиме"""
        if not self.DEBUG:
            if self.JWT_SECRET_KEY == "dev-insecure-secret-key-change-in-production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set via USER_JWT_SECRET_KEY environment variable in production"
                )
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via USER_SERVICE_API_KEY environment variable in production"
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
