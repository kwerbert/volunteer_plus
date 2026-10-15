from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    SERVICE_NAME: str = "event_service"
    SERVICE_PORT: int = 8003
    DEBUG: bool = True
    _project_root: Path = Path(__file__).resolve().parents[3]
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_project_root}/volunteer_plus.db"
    LOG_LEVEL: str = "INFO"
    SERVICE_API_KEY: str = Field(default="dev-insecure-service-key-change-in-production")
    CHAT_SERVICE_URL: str = Field(default="http://localhost:8007", description="URL чат-сервиса")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="EVENT_"
    )

    @model_validator(mode='after')
    def validate_secrets_for_production(self):
        """Проверка, что секретные ключи заменены в production-режиме"""
        if not self.DEBUG:
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError(
                    "SERVICE_API_KEY must be set via EVENT_SERVICE_API_KEY environment variable in production"
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