from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    SERVICE_NAME: str = "chat_service"
    SERVICE_PORT: int = 8007
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    _project_root: Path = Path(__file__).resolve().parents[3]
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_project_root}/volunteer_plus.db"
    SERVICE_API_KEY: str = Field(default="dev-insecure-service-key-change-in-production")
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production",
        description="JWT secret key (env: CHAT_JWT_SECRET_KEY). "
                    "Должен совпадать с USER_JWT_SECRET_KEY.",
    )
    JWT_ALGORITHM: str = "HS256"
    USER_SERVICE_URL: str = "http://localhost:8008"
    ORGANIZATION_SERVICE_URL: str = "http://localhost:8004"
    EVENT_SERVICE_URL: str = "http://localhost:8003"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://10.0.2.2:3000,http://10.0.2.2:8007"
    # Добавлено для тестов
    DEFAULT_PAGE_SIZE: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="CHAT_"
    )

    @model_validator(mode='after')
    def validate_secrets_for_production(self):
        if not self.DEBUG:
            if self.JWT_SECRET_KEY == "dev-insecure-secret-key-change-in-production":
                raise ValueError("JWT_SECRET_KEY must be set via CHAT_JWT_SECRET_KEY")
            if self.SERVICE_API_KEY == "dev-insecure-service-key-change-in-production":
                raise ValueError("SERVICE_API_KEY must be set via CHAT_SERVICE_API_KEY")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

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