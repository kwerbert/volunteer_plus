from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "event_service"
    SERVICE_PORT: int = 8003
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/volunteer_plus"
    LOG_LEVEL: str = "INFO"

    SERVICE_API_KEY: str = Field(
        default="dev-insecure-service-key-change-in-production"
    )
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production",
        description="JWT secret key (env: EVENT_JWT_SECRET_KEY). "
        "Должен совпадать с USER_JWT_SECRET_KEY.",
    )
    JWT_ALGORITHM: str = "HS256"

    CHAT_SERVICE_URL: str = Field(
        default="http://localhost:8007", description="URL чат-сервиса"
    )
    ORGANIZATION_SERVICE_URL: str = Field(
        default="http://localhost:8004",
        description="URL organization-сервиса (проверка прав)",
    )
    USER_SERVICE_URL: str = Field(
        default="http://localhost:8008",
        description="URL user-сервиса (проверка is_admin при отмене)",
    )
    NOTIFICATION_SERVICE_URL: str = Field(
        default="http://localhost:8006",
        description="URL notification-сервиса",
    )
    ANALYTICS_SERVICE_URL: str = Field(
        default="http://localhost:8005",
        description="URL analytics-сервиса (учёт часов при завершении)",
    )
    # Триггер учёта часов при active→completed. Выключается в тестах:
    # EVENT_ANALYTICS_TRIGGER_ENABLED=false
    ANALYTICS_TRIGGER_ENABLED: bool = True

    # === Жизненный цикл ===
    CANCELLED_RETENTION_DAYS: int = 30  # 4.3: физическое удаление через 30 дней
    MAINTENANCE_ENABLED: bool = True  # фоновая задача завершения/очистки
    MAINTENANCE_INTERVAL_SECONDS: int = 3600
    NOTIFICATION_TIMEOUT_SECONDS: float = 3.0

    # Дефолтная роль волонтёра, если организатор не задал роли
    DEFAULT_EVENT_HOURS: float = 4.0
    DEFAULT_ROLE_NAME: str = "Участник"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="EVENT_",
    )

    @model_validator(mode="after")
    def validate_secrets_for_production(self):
        if not self.DEBUG:
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via EVENT_SERVICE_API_KEY"
                )
            if self.JWT_SECRET_KEY == "dev-insecure-secret-key-change-in-production":
                raise ValueError("JWT_SECRET_KEY must be set via EVENT_JWT_SECRET_KEY")
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
