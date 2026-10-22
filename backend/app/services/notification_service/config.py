from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
from enum import Enum
from typing import Optional
from app.utils.notifications_enums import (
    Platform,
    NotificationType,
    Priority,
    PushStatus,
)

class Settings(BaseSettings):
    SERVICE_NAME: str = "notification_service"
    SERVICE_PORT: int = 8006
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    # Пути
    _project_root: Path = Path(__file__).resolve().parents[3]
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_project_root}/volunteer_plus.db"
    # Firebase
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(
        default=None,
        description="Path to Firebase service account JSON (env: NOTIFICATION_FIREBASE_CREDENTIALS_PATH)"
    )
    FIREBASE_PROJECT_ID: str = "volunteer-plus-cf4e5"
    # Сервисы
    USER_SERVICE_URL: str = "http://localhost:8008"
    CHAT_SERVICE_URL: str = "http://localhost:8007"
    # Безопасность — загружаются из переменных окружения с NOTIFICATION_ префиксом
    SERVICE_API_KEY: str = Field(
        default="dev-insecure-service-key-change-in-production",
        description="Service-to-service API key (env: NOTIFICATION_SERVICE_API_KEY)"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production",
        description="JWT secret key (env: NOTIFICATION_JWT_SECRET_KEY)"
    )
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    # Push
    PUSH_RETRY_ATTEMPTS: int = 3
    PUSH_TTL_SECONDS: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="NOTIFICATION_",
    )

    @model_validator(mode='after')
    def validate_secrets_for_production(self):
        """Проверка, что секретные ключи заменены в production-режиме"""
        if not self.DEBUG:
            if self.JWT_SECRET_KEY == "dev-insecure-secret-key-change-in-production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set via NOTIFICATION_JWT_SECRET_KEY environment variable in production"
                )
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via NOTIFICATION_SERVICE_API_KEY environment variable in production"
                )
        return self

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()