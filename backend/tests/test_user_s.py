"""
Тесты User Service (pytest версия)
"""
import pytest
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================================
# КРИТИЧЕСКИ ВАЖНО: Настройка путей ДО любого импорта модулей проекта
# ============================================================================
# Добавляем корень проекта в sys.path (1 уровень вверх от файла теста)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ (чтобы не повторять код)
# ============================================================================
def now_utc() -> datetime:
    """Возвращает текущее время в UTC (timezone-aware)"""
    return datetime.now(timezone.utc)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    """Фикстура для мок-сессии БД"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    return session


@pytest.fixture
def mock_user_repo():
    """Фикстура для мок-репозитория пользователей"""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_email = AsyncMock()
    repo.exists = AsyncMock()
    repo.update = AsyncMock()
    repo.update_last_login = AsyncMock()
    repo.get_settings = AsyncMock()
    repo.create_settings = AsyncMock()
    repo.update_settings = AsyncMock()
    repo.get_location = AsyncMock()
    repo.update_location = AsyncMock()
    repo.create_refresh_token = AsyncMock()
    repo.is_token_revoked = AsyncMock()
    repo.revoke_token = AsyncMock()
    return repo


@pytest.fixture
def clear_user_settings_cache():
    """Очистка кэша настроек перед тестом"""
    try:
        from app.services.user_service.config import get_settings
        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from app.services.user_service.config import get_settings
        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass


# ============================================================================
# ТЕСТЫ КОНФИГУРАЦИИ
# ============================================================================

class TestConfig:
    """Тесты конфигурации сервиса"""

    def test_001_config_settings(self, clear_user_settings_cache):
        """Проверка загрузки настроек из конфигурации"""
        from app.services.user_service.config import get_settings
        settings = get_settings()

        assert settings.SERVICE_PORT == 8008, f"Порт должен быть 8008, получено {settings.SERVICE_PORT}"
        assert settings.SERVICE_NAME == "user_service"
        assert "sqlite+aiosqlite" in settings.DATABASE_URL
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.SERVICE_API_KEY is not None
        print("✓ Конфигурация загружена корректно")

    def test_002_config_cors_origins(self, clear_user_settings_cache):
        """Проверка парсинга CORS origins"""
        from app.services.user_service.config import get_settings
        settings = get_settings()

        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) > 0
        print("✓ CORS origins распарсены корректно")


# ============================================================================
# ТЕСТЫ СХЕМ (PYDANTIC V2)
# ============================================================================

class TestSchemas:
    """Тесты Pydantic схем"""

    def test_003_register_request_schema(self):
        """Проверка схемы регистрации"""
        from app.services.user_service.api.schemas import RegisterRequest
        from pydantic import ValidationError

        req = RegisterRequest(
            email="user@example.com",
            password="secure_password_123",
            full_name="Иван Иванов",
            phone="+79991234567"
        )
        assert req.email == "user@example.com"
        assert req.full_name == "Иван Иванов"

        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="short")

        with pytest.raises(ValidationError):
            RegisterRequest(email="invalid-email", password="secure_password_123")

        print("✓ Схема регистрации валидируется корректно")

    def test_004_location_request_schema(self):
        """Проверка схемы геолокации"""
        from app.services.user_service.api.schemas import LocationRequest
        from pydantic import ValidationError

        req = LocationRequest(
            latitude=55.7558,
            longitude=37.6173,
            accuracy=10.5
        )
        assert req.latitude == 55.7558
        assert req.longitude == 37.6173

        with pytest.raises(ValidationError):
            LocationRequest(latitude=95.0, longitude=37.6173)

        with pytest.raises(ValidationError):
            LocationRequest(latitude=55.7558, longitude=200.0)

        print("✓ Схема геолокации валидируется корректно")

    def test_005_settings_update_schema(self):
        """Проверка схемы обновления настроек"""
        from app.services.user_service.api.schemas import UserSettingsUpdateRequest
        from pydantic import ValidationError

        req = UserSettingsUpdateRequest(
            search_radius_km=25,
            show_only_subscriptions=True
        )
        assert req.search_radius_km == 25

        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(language="de")

        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(theme="blue")

        print("✓ Схема настроек валидируется корректно")


# ============================================================================
# ТЕСТЫ SECURITY (PASSWORD & JWT)
# ============================================================================

class TestSecurity:
    """Тесты безопасности"""

    def test_006_password_hash_and_verify(self):
        """Проверка хеширования и проверки пароля"""
        from app.services.user_service.core.security import hash_password, verify_password

        password = "secure_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2")

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

        print("✓ Хеширование пароля работает корректно")

    def test_007_jwt_token_creation_and_decode(self):
        """Проверка создания и декодирования JWT токенов"""
        from app.services.user_service.core.security import (
            create_access_token, create_refresh_token, decode_token
        )

        token_data = {"user_id": 1, "email": "user@example.com", "role": "volunteer"}

        access_token = create_access_token(token_data)
        assert access_token is not None

        payload = decode_token(access_token, token_type="access")
        assert payload is not None
        assert payload["user_id"] == 1

        refresh_token = create_refresh_token(token_data)
        payload = decode_token(refresh_token, token_type="refresh")
        assert payload is not None

        print("✓ JWT токены создаются и декодируются корректно")


# ============================================================================
# ТЕСТЫ AUTH SERVICE
# ============================================================================

@pytest.mark.asyncio
class TestAuthService:
    """Тесты сервиса аутентификации"""

    async def test_008_register_user(self, mock_user_repo):
        """Проверка регистрации пользователя"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.db.models import User, UserSettings, UserRoleEnum

        mock_user = User(
            id=1,
            email="newuser@example.com",
            password_hash="$2b$12$hashed",
            full_name="New User",
            role=UserRoleEnum.VOLUNTEER,
            is_active=True,
            created_at=now_utc()
        )
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.create.return_value = mock_user
        mock_user_repo.create_settings.return_value = UserSettings(user_id=1)

        auth_service = AuthService(mock_user_repo)
        user_data, tokens = await auth_service.register(
            email="newuser@example.com",
            password="secure_password_123",
            full_name="New User"
        )

        assert user_data["email"] == "newuser@example.com"
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        print("✓ Регистрация пользователя работает корректно")

    async def test_009_login_user(self, mock_user_repo):
        """Проверка логина пользователя"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.security import hash_password
        from app.services.user_service.db.models import User, UserRoleEnum

        password = "secure_password_123"
        mock_user = User(
            id=1,
            email="user@example.com",
            password_hash=hash_password(password),
            full_name="Test User",
            role=UserRoleEnum.VOLUNTEER,
            is_active=True,
            created_at=now_utc()
        )
        mock_user_repo.get_by_email.return_value = mock_user

        auth_service = AuthService(mock_user_repo)
        user_data, tokens = await auth_service.login(
            email="user@example.com",
            password=password
        )

        assert user_data["email"] == "user@example.com"
        assert "access_token" in tokens

        print("✓ Логин пользователя работает корректно")

    async def test_010_login_wrong_password(self, mock_user_repo):
        """Проверка логина с неверным паролем"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.security import hash_password
        from app.services.user_service.db.models import User, UserRoleEnum

        mock_user = User(
            id=1,
            email="user@example.com",
            password_hash=hash_password("correct_password"),
            role=UserRoleEnum.VOLUNTEER,
            is_active=True,
            created_at=now_utc()
        )
        mock_user_repo.get_by_email.return_value = mock_user

        auth_service = AuthService(mock_user_repo)

        with pytest.raises(ValueError, match="Неверный email или пароль"):
            await auth_service.login(
                email="user@example.com",
                password="wrong_password"
            )

        print("✓ Логин с неверным паролем отклоняется корректно")

    async def test_011_logout_revoke_token(self, mock_user_repo):
        """Проверка выхода (отзыв токена)"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.security import hash_token_for_blacklist

        refresh_token = "mock_refresh_token_12345"
        token_hash = hash_token_for_blacklist(refresh_token)

        auth_service = AuthService(mock_user_repo)
        await auth_service.logout(refresh_token)

        mock_user_repo.revoke_token.assert_called_once_with(token_hash)

        print("✓ Выход (отзыв токена) работает корректно")


# ============================================================================
# ТЕСТЫ USER SERVICE
# ============================================================================

@pytest.mark.asyncio
class TestUserService:
    """Тесты основного сервиса пользователей"""

    async def test_012_get_user_profile(self, mock_user_repo, mock_session):
        """Проверка получения профиля пользователя"""
        from app.services.user_service.core.service import UserService
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.db.models import User, UserSettings, UserLocation, UserRoleEnum

        mock_user = User(
            id=1,
            email="user@example.com",
            full_name="Test User",
            role=UserRoleEnum.VOLUNTEER,
            is_active=True,
            is_verified=False,
            created_at=now_utc()
        )
        mock_settings = UserSettings(
            id=1, user_id=1, search_radius_km=10,
            language="ru", theme="light",
            updated_at=now_utc()
        )
        mock_location = UserLocation(
            id=1, user_id=1, latitude=55.7558, longitude=37.6173,
            accuracy=10.0,
            updated_at=now_utc()
        )

        mock_user_repo.get_by_id.return_value = mock_user
        mock_user_repo.get_settings.return_value = mock_settings
        mock_user_repo.get_location.return_value = mock_location

        auth_service = AuthService(mock_user_repo)
        user_service = UserService(mock_user_repo, auth_service)

        profile = await user_service.get_user_profile(1)

        assert profile is not None
        assert profile["user"]["email"] == "user@example.com"

        print("✓ Получение профиля пользователя работает корректно")

    async def test_013_update_user_location(self, mock_user_repo, mock_session):
        """Проверка обновления геолокации"""
        from app.services.user_service.core.service import UserService
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.db.models import UserLocation

        mock_location = UserLocation(
            id=1, user_id=1, latitude=55.7558, longitude=37.6173,
            accuracy=10.0,
            updated_at=now_utc()
        )
        mock_user_repo.update_location.return_value = mock_location

        auth_service = AuthService(mock_user_repo)
        user_service = UserService(mock_user_repo, auth_service)

        location = await user_service.update_user_location(
            user_id=1,
            latitude=55.7558,
            longitude=37.6173,
            accuracy=10.0
        )

        assert location["latitude"] == 55.7558
        assert location["longitude"] == 37.6173

        print("✓ Обновление геолокации работает корректно")

    async def test_014_verify_user_exists(self, mock_user_repo):
        """Проверка existence пользователя (для service-to-service)"""
        from app.services.user_service.core.service import UserService
        from app.services.user_service.core.auth_service import AuthService

        mock_user_repo.exists.return_value = True

        auth_service = AuthService(mock_user_repo)
        user_service = UserService(mock_user_repo, auth_service)

        exists = await user_service.verify_user_exists(1)

        assert exists is True

        print("✓ Проверка существования пользователя работает корректно")


# ============================================================================
# ТЕСТЫ DEPENDENCIES (AUTH & SERVICE-KEY)
# ============================================================================

@pytest.mark.asyncio
class TestDependencies:
    """Тесты зависимостей"""

    async def test_015_verify_service_key_valid(self):
        """Проверка валидного API ключа сервиса"""
        from app.services.user_service.api.deps import verify_service_key

        with patch('app.services.user_service.api.deps.settings') as mock_settings:
            mock_settings.SERVICE_API_KEY = "valid-service-key"

            result = await verify_service_key(x_service_key="valid-service-key")
            assert result is True

        print("✓ Валидный API ключ сервиса принимается")

    async def test_016_verify_service_key_invalid(self):
        """Проверка невалидного API ключа сервиса"""
        from app.services.user_service.api.deps import verify_service_key
        from fastapi import HTTPException

        with patch('app.services.user_service.api.deps.settings') as mock_settings:
            mock_settings.SERVICE_API_KEY = "valid-service-key"

            with pytest.raises(HTTPException) as exc_info:
                await verify_service_key(x_service_key="invalid-key")

            assert exc_info.value.status_code == 403

        print("✓ Невалидный API ключ сервиса отклоняется")

    async def test_017_verify_service_key_missing(self):
        """Проверка отсутствующего API ключа сервиса"""
        from app.services.user_service.api.deps import verify_service_key
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_service_key(x_service_key=None)

        assert exc_info.value.status_code == 401

        print("✓ Отсутствующий API ключ сервиса отклоняется")


# ============================================================================
# ТЕСТЫ FASTAPI ПРИЛОЖЕНИЯ
# ============================================================================

class TestMainApp:
    """Тесты FastAPI приложения"""

    def test_018_app_creation(self, clear_user_settings_cache):
        """Проверка создания FastAPI приложения"""
        from app.services.user_service.main import app

        assert app is not None
        assert app.title == "user_service"
        assert app.version == "1.0.0"

        print("✓ FastAPI приложение создано корректно")

    def test_019_app_routes(self, clear_user_settings_cache):
        """Проверка подключенных роутов (рекурсивно по вложенным роутерам)"""
        from app.services.user_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)

        assert "/api/v1/auth/register" in routes
        assert "/api/v1/auth/login" in routes
        assert "/api/v1/auth/refresh" in routes
        assert "/api/v1/auth/logout" in routes
        assert "/api/v1/users/{user_id}" in routes
        assert "/api/v1/users/{user_id}/location" in routes
        assert "/api/v1/users/{user_id}/settings" in routes
        assert "/api/v1/users/verify/{user_id}" in routes
        assert "/api/v1/users/{user_id}/profile" in routes
        assert "/health" in routes
        assert "/" in routes

        print("✓ Все эндпоинты подключены корректно")

    def test_020_health_endpoint(self, clear_user_settings_cache):
        """Проверка health endpoint"""
        from app.services.user_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)
        assert routes.count("/health") == 1

        print("✓ Health endpoint доступен")


# ============================================================================
# ЗАПУСК ТЕСТОВ
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ USER SERVICE (pytest)")
    print("=" * 80)
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])
    print("\n" + "=" * 80)
    print(f"КОД ВЫХОДА: {exit_code}")
    print("=" * 80)
    sys.exit(exit_code)

# pytest tests/test_user_s.py -v
