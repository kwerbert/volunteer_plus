import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def now_utc() -> datetime:
    """Возвращает текущее время в UTC (timezone-aware)"""
    return datetime.now(timezone.utc)


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


class TestConfig:
    """Тесты конфигурации сервиса"""

    def test_001_config_settings(self, clear_user_settings_cache):
        """Проверка загрузки настроек из конфигурации"""
        from app.services.user_service.config import get_settings

        settings = get_settings()

        assert settings.SERVICE_PORT == 8008, (
            f"Порт должен быть 8008, получено {settings.SERVICE_PORT}"
        )
        assert settings.SERVICE_NAME == "user_service"
        assert "postgresql+asyncpg" in settings.DATABASE_URL
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.SERVICE_API_KEY is not None
        print("Конфигурация загружена корректно")

    def test_002_config_cors_origins(self, clear_user_settings_cache):
        """Проверка парсинга CORS origins"""
        from app.services.user_service.config import get_settings

        settings = get_settings()

        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) > 0
        print("CORS origins распарсены корректно")


class TestSchemas:
    """Тесты Pydantic схем"""

    def test_003_register_request_schema(self):
        """Проверка схемы регистрации"""
        from pydantic import ValidationError

        from app.services.user_service.api.schemas import RegisterRequest

        req = RegisterRequest(
            email="user@example.com",
            password="secure_password_123",
            full_name="Иван Иванов",
            phone="+79991234567",
        )
        assert req.email == "user@example.com"
        assert req.full_name == "Иван Иванов"

        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="short")

        with pytest.raises(ValidationError):
            RegisterRequest(email="invalid-email", password="secure_password_123")

        print("Схема регистрации валидируется корректно")

    def test_004_location_request_schema(self):
        """Проверка схемы геолокации"""
        from pydantic import ValidationError

        from app.services.user_service.api.schemas import LocationRequest

        req = LocationRequest(latitude=55.7558, longitude=37.6173, accuracy=10.5)
        assert req.latitude == 55.7558
        assert req.longitude == 37.6173

        with pytest.raises(ValidationError):
            LocationRequest(latitude=95.0, longitude=37.6173)

        with pytest.raises(ValidationError):
            LocationRequest(latitude=55.7558, longitude=200.0)

        print("Схема геолокации валидируется корректно")

    def test_005_settings_update_schema(self):
        """Проверка схемы обновления настроек"""
        from pydantic import ValidationError

        from app.services.user_service.api.schemas import UserSettingsUpdateRequest

        req = UserSettingsUpdateRequest(
            search_radius_km=25, show_only_subscriptions=True
        )
        assert req.search_radius_km == 25

        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(language="de")

        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(theme="blue")

        print("Схема настроек валидируется корректно")


class TestSecurity:
    """Тесты безопасности"""

    def test_006_password_hash_and_verify(self):
        """Проверка хеширования и проверки пароля"""
        from app.services.user_service.core.security import (
            hash_password,
            verify_password,
        )

        password = "secure_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2")

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

        print("Хеширование пароля работает корректно")

    def test_007_jwt_token_creation_and_decode(self):
        """Проверка создания и декодирования JWT токенов"""
        from app.services.user_service.core.security import (
            create_access_token,
            create_refresh_token,
            decode_token,
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

        print("JWT токены создаются и декодируются корректно")


@pytest.mark.asyncio
class TestAuthService:
    async def test_008_register_user(self, mock_user_repo):
        """Проверка регистрации пользователя"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.db.models import User, UserRoleEnum, UserSettings

        mock_user = User(
            id=1,
            email="newuser@example.com",
            password_hash="$2b$12$hashed",
            full_name="New User",
            role=UserRoleEnum.VOLUNTEER,
            is_active=True,
            created_at=now_utc(),
        )
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.create.return_value = mock_user
        mock_user_repo.create_settings.return_value = UserSettings(user_id=1)

        auth_service = AuthService(mock_user_repo)
        user_data, tokens = await auth_service.register(
            email="newuser@example.com",
            password="secure_password_123",
            full_name="New User",
        )

        assert user_data["email"] == "newuser@example.com"
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        print("Регистрация пользователя работает корректно")

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
            created_at=now_utc(),
        )
        mock_user_repo.get_by_email.return_value = mock_user

        auth_service = AuthService(mock_user_repo)
        user_data, tokens = await auth_service.login(
            email="user@example.com", password=password
        )

        assert user_data["email"] == "user@example.com"
        assert "access_token" in tokens

        print("Логин пользователя работает корректно")

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
            created_at=now_utc(),
        )
        mock_user_repo.get_by_email.return_value = mock_user

        auth_service = AuthService(mock_user_repo)

        with pytest.raises(ValueError, match="Неверный email или пароль"):
            await auth_service.login(
                email="user@example.com", password="wrong_password"
            )

        print("Логин с неверным паролем отклоняется корректно")

    async def test_011_logout_revoke_token(self, mock_user_repo):
        """Проверка выхода (отзыв токена)"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.security import hash_token_for_blacklist

        refresh_token = "mock_refresh_token_12345"
        token_hash = hash_token_for_blacklist(refresh_token)

        auth_service = AuthService(mock_user_repo)
        await auth_service.logout(refresh_token)

        mock_user_repo.revoke_token.assert_called_once_with(token_hash)

        print("Выход (отзыв токена) работает корректно")


@pytest.mark.asyncio
class TestUserService:
    """Тесты основного сервиса пользователей"""

    async def test_012_get_user_profile(self, mock_user_repo, mock_session):
        """Проверка получения профиля пользователя"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.service import UserService
        from app.services.user_service.db.models import (
            User,
            UserLocation,
            UserRoleEnum,
            UserSettings,
        )

        mock_user = User(
            id=1,
            email="user@example.com",
            full_name="Test User",
            role=UserRoleEnum.VOLUNTEER,
            is_active=True,
            is_verified=False,
            created_at=now_utc(),
        )
        mock_settings = UserSettings(
            id=1,
            user_id=1,
            search_radius_km=10,
            language="ru",
            theme="light",
            updated_at=now_utc(),
        )
        mock_location = UserLocation(
            id=1,
            user_id=1,
            latitude=55.7558,
            longitude=37.6173,
            accuracy=10.0,
            updated_at=now_utc(),
        )

        mock_user_repo.get_by_id.return_value = mock_user
        mock_user_repo.get_settings.return_value = mock_settings
        mock_user_repo.get_location.return_value = mock_location

        auth_service = AuthService(mock_user_repo)
        user_service = UserService(mock_user_repo, auth_service)

        profile = await user_service.get_user_profile(1)

        assert profile is not None
        assert profile["user"]["email"] == "user@example.com"

        print("Получение профиля пользователя работает корректно")

    async def test_013_update_user_location(self, mock_user_repo, mock_session):
        """Проверка обновления геолокации"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.service import UserService
        from app.services.user_service.db.models import UserLocation

        mock_location = UserLocation(
            id=1,
            user_id=1,
            latitude=55.7558,
            longitude=37.6173,
            accuracy=10.0,
            updated_at=now_utc(),
        )
        mock_user_repo.update_location.return_value = mock_location

        auth_service = AuthService(mock_user_repo)
        user_service = UserService(mock_user_repo, auth_service)

        location = await user_service.update_user_location(
            user_id=1, latitude=55.7558, longitude=37.6173, accuracy=10.0
        )

        assert location["latitude"] == 55.7558
        assert location["longitude"] == 37.6173

        print("Обновление геолокации работает корректно")

    async def test_014_verify_user_exists(self, mock_user_repo):
        """Проверка existence пользователя (для service-to-service)"""
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.service import UserService

        mock_user_repo.exists.return_value = True

        auth_service = AuthService(mock_user_repo)
        user_service = UserService(mock_user_repo, auth_service)

        exists = await user_service.verify_user_exists(1)

        assert exists is True

        print("Проверка существования пользователя работает корректно")


@pytest.mark.asyncio
class TestDependencies:
    """Тесты зависимостей"""

    async def test_015_verify_service_key_valid(self):
        """Проверка валидного API ключа сервиса"""
        from app.services.user_service.api.deps import verify_service_key

        with patch("app.services.user_service.api.deps.settings") as mock_settings:
            mock_settings.SERVICE_API_KEY = "valid-service-key"

            result = await verify_service_key(x_service_key="valid-service-key")
            assert result is True

        print("Валидный API ключ сервиса принимается")

    async def test_016_verify_service_key_invalid(self):
        """Проверка невалидного API ключа сервиса"""
        from fastapi import HTTPException

        from app.services.user_service.api.deps import verify_service_key

        with patch("app.services.user_service.api.deps.settings") as mock_settings:
            mock_settings.SERVICE_API_KEY = "valid-service-key"

            with pytest.raises(HTTPException) as exc_info:
                await verify_service_key(x_service_key="invalid-key")

            assert exc_info.value.status_code == 403

        print("Невалидный API ключ сервиса отклоняется")

    async def test_017_verify_service_key_missing(self):
        """Проверка отсутствующего API ключа сервиса"""
        from fastapi import HTTPException

        from app.services.user_service.api.deps import verify_service_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_service_key(x_service_key=None)

        assert exc_info.value.status_code == 401

        print("Отсутствующий API ключ сервиса отклоняется")


class TestMainApp:
    """Тесты FastAPI приложения"""

    def test_018_app_creation(self, clear_user_settings_cache):
        """Проверка создания FastAPI приложения"""
        from app.services.user_service.main import app

        assert app is not None
        assert app.title == "user_service"
        assert app.version == "1.0.0"

        print("FastAPI приложение создано корректно")

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

        print("Все эндпоинты подключены корректно")

    def test_020_health_endpoint(self, clear_user_settings_cache):
        """Проверка health endpoint"""
        from app.services.user_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)
        assert routes.count("/health") == 1

        print("Health endpoint доступен")

    def test_021_organizer_application_routes(self, clear_user_settings_cache):
        """Проверка маршрутов заявок организатора"""
        from app.services.user_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)

        assert "/api/v1/organizer-applications" in routes
        assert "/api/v1/organizer-applications/me" in routes
        assert "/api/v1/organizer-applications/{application_id}" in routes

        print("Эндпоинты заявок организатора подключены корректно")


class TestStage2InternalAPI:
    def test_022_by_email_route_registered(self, clear_user_settings_cache):
        from app.services.user_service.main import app
        from tests.conftest import collect_route_paths

        assert "/api/v1/users/by-email/{email}" in collect_route_paths(app)

    def test_023_verify_response_schema_extended(self):
        from app.services.user_service.api.schemas import UserVerifyResponse

        resp = UserVerifyResponse(
            user_id=2, exists=True, is_active=True, role="organizer", is_admin=False
        )
        assert resp.role == "organizer"
        # Обратная совместимость: новые поля опциональны
        legacy = UserVerifyResponse(user_id=1, exists=False, is_active=False)
        assert legacy.role is None and legacy.is_admin is False

    @pytest.mark.asyncio
    async def test_024_get_user_by_email(self, mock_user_repo):
        from app.services.user_service.core.auth_service import AuthService
        from app.services.user_service.core.service import UserService
        from app.services.user_service.db.models import User, UserRoleEnum

        mock_user_repo.get_by_email.return_value = User(
            id=2,
            email="org@example.com",
            password_hash="x",
            role=UserRoleEnum.ORGANIZER,
            is_active=True,
            is_admin=False,
            created_at=now_utc(),
        )
        service = UserService(mock_user_repo, AuthService(mock_user_repo))
        user = await service.get_user_by_email("org@example.com")
        assert user is not None and user.role == UserRoleEnum.ORGANIZER
        mock_user_repo.get_by_email.assert_awaited_once_with("org@example.com")


from datetime import timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.services.user_service.api.deps import (
    get_current_user_id as user_get_uid,
)
from app.services.user_service.api.deps import (
    get_db as user_get_db,
)
from app.services.user_service.core.security import hash_password
from app.services.user_service.db.models import (
    Base as UserBase,
)
from app.services.user_service.db.models import (
    OrganizerApplication,
    OrganizerApplicationStatus,
    User,
    UserRoleEnum,
)
from app.services.user_service.main import app as user_app

_USER_TEST_DB = "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/volunteer_plus_test"
_u_engine = create_async_engine(_USER_TEST_DB, echo=False, future=True)
_u_factory = async_sessionmaker(_u_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture()
async def udb():
    """Тестовая БД user_service: таблицы → сессия → очистка."""
    async with _u_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
    async with _u_factory() as session:
        yield session
    async with _u_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.drop_all)


@pytest.fixture()
async def uclient(udb):
    """HTTP-клиент с подменой get_db на тестовую сессию."""

    async def _override_db():
        yield udb

    user_app.dependency_overrides[user_get_db] = _override_db
    transport = ASGITransport(app=user_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    user_app.dependency_overrides.clear()


def _login(user_id: int):
    """Подмена JWT-аутентификации: возвращаем конкретный user_id."""
    user_app.dependency_overrides[user_get_uid] = lambda: user_id


async def _mk_user(
    db, uid, email, role=UserRoleEnum.VOLUNTEER, is_admin=False, is_active=True
):
    """Создаёт пользователя в тестовой БД."""
    u = User(
        id=uid,
        email=email,
        password_hash=hash_password("Passw0rd!"),
        full_name=f"User {uid}",
        role=role,
        is_admin=is_admin,
        is_active=is_active,
    )
    db.add(u)
    await db.flush()
    return u


async def _mk_application(
    db, user_id, status, reviewed_at=None, reviewed_by=None, reason=None
):
    """Создаёт заявку напрямую в БД (для подготовки сценариев)."""
    app = OrganizerApplication(
        user_id=user_id,
        status=status,
        reviewed_at=reviewed_at,
        reviewed_by=reviewed_by,
        rejection_reason=reason,
    )
    db.add(app)
    await db.flush()
    return app


@pytest.mark.asyncio
class TestOrganizerApplications:
    # ---------- Подача заявки ----------

    async def test_025_volunteer_creates_application(self, uclient, udb):
        """Волонтёр подаёт заявку → 201, статус pending."""
        await _mk_user(udb, 1, "vol@test.com")
        await udb.commit()
        _login(1)

        resp = await uclient.post("/api/v1/organizer-applications")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["user_id"] == 1
        assert data["status"] == "pending"
        assert data["reviewed_by"] is None
        assert data["reviewed_at"] is None

    async def test_026_organizer_cannot_apply(self, uclient, udb):
        """Пользователь уже ORGANIZER → 400."""
        await _mk_user(udb, 2, "org@test.com", role=UserRoleEnum.ORGANIZER)
        await udb.commit()
        _login(2)

        resp = await uclient.post("/api/v1/organizer-applications")
        assert resp.status_code == 400
        assert "организатором" in resp.json()["detail"].lower()

    async def test_027_pending_duplicate_409(self, uclient, udb):
        """Активная заявка (pending) уже есть → 409."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(1)

        resp = await uclient.post("/api/v1/organizer-applications")
        assert resp.status_code == 409

    async def test_028_cooldown_after_rejection_429(self, uclient, udb):
        """Отклонена менее 1 часа назад → 429 с временем повтора."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        await _mk_application(
            udb,
            1,
            OrganizerApplicationStatus.REJECTED,
            reviewed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            reviewed_by=3,
            reason="Недостаточно данных",
        )
        await udb.commit()
        _login(1)

        resp = await uclient.post("/api/v1/organizer-applications")
        assert resp.status_code == 429
        detail = resp.json()["detail"]
        assert "retry_at" in detail
        assert "retry_after_seconds" in detail
        assert detail["retry_after_seconds"] > 0
        assert "Retry-After" in resp.headers

    async def test_029_apply_after_cooldown(self, uclient, udb):
        """Отклонена более 1 часа назад → повторная подача разрешена (201)."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        await _mk_application(
            udb,
            1,
            OrganizerApplicationStatus.REJECTED,
            reviewed_at=datetime.now(timezone.utc) - timedelta(hours=2),
            reviewed_by=3,
            reason="Старое отклонение",
        )
        await udb.commit()
        _login(1)

        resp = await uclient.post("/api/v1/organizer-applications")
        assert resp.status_code == 201, resp.text

    # ---------- Получение своей заявки ----------

    async def test_030_get_my_latest_application(self, uclient, udb):
        """GET /me возвращает последнюю заявку."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        await _mk_application(
            udb, 1, OrganizerApplicationStatus.REJECTED, reviewed_by=3
        )
        app2 = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(1)

        resp = await uclient.get("/api/v1/organizer-applications/me")
        assert resp.status_code == 200
        assert resp.json()["id"] == app2.id
        assert resp.json()["status"] == "pending"

    async def test_031_get_my_application_404(self, uclient, udb):
        """Заявок не было → 404."""
        await _mk_user(udb, 1, "vol@test.com")
        await udb.commit()
        _login(1)

        resp = await uclient.get("/api/v1/organizer-applications/me")
        assert resp.status_code == 404

    # ---------- Одобрение / отклонение ----------

    async def test_032_admin_approves_application(self, uclient, udb):
        """Админ одобряет → роль пользователя меняется на ORGANIZER."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        app = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "approved"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "approved"
        assert data["reviewed_by"] == 3
        assert data["reviewed_at"] is not None
        assert data["rejection_reason"] is None

        # Проверяем смену роли в БД
        user = await udb.get(User, 1)
        await udb.refresh(user)
        assert user.role == UserRoleEnum.ORGANIZER

    async def test_033_admin_rejects_with_reason(self, uclient, udb):
        """Админ отклоняет с указанием причины. Роль не меняется."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        app = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "rejected", "rejection_reason": "Мало опыта"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Мало опыта"

        user = await udb.get(User, 1)
        await udb.refresh(user)
        assert user.role == UserRoleEnum.VOLUNTEER  # не изменилась

    async def test_034_non_admin_cannot_review(self, uclient, udb):
        """Не админ пытается рассмотреть заявку → 403."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 2, "vol2@test.com")  # обычный волонтёр
        app = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(2)

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "approved"},
        )
        assert resp.status_code == 403

    async def test_035_review_nonexistent_404(self, uclient, udb):
        """Заявка не найдена → 404."""
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            "/api/v1/organizer-applications/99999",
            json={"status": "approved"},
        )
        assert resp.status_code == 404

    async def test_036_review_already_reviewed_409(self, uclient, udb):
        """Заявка уже рассмотрена → 409."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        await _mk_application(
            udb,
            1,
            OrganizerApplicationStatus.APPROVED,
            reviewed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            reviewed_by=3,
        )
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            "/api/v1/organizer-applications/1",
            json={"status": "rejected"},
        )
        assert resp.status_code == 409

    async def test_037_self_review_forbidden(self, uclient, udb):
        """Админ не может рассматривать собственную заявку → 403."""
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        app = await _mk_application(udb, 3, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "approved"},
        )
        assert resp.status_code == 403

    async def test_038_review_deactivated_user_404(self, uclient, udb):
        """Пользователь деактивирован → 404 при рассмотрении."""
        await _mk_user(udb, 1, "vol@test.com", is_active=False)
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        app = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "approved"},
        )
        assert resp.status_code == 404

    # ---------- Зависимость require_admin ----------

    async def test_039_require_admin_passes(self, uclient, udb):
        """is_admin=True → доступ к защищённому эндпоинту."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 3, "admin@test.com", is_admin=True)
        app = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(3)

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "approved"},
        )
        assert resp.status_code == 200

    async def test_040_require_admin_denies_volunteer(self, uclient, udb):
        """is_admin=False → 403 (проверка зависимости require_admin)."""
        await _mk_user(udb, 1, "vol@test.com")
        await _mk_user(udb, 4, "vol_organizer@test.com", role=UserRoleEnum.ORGANIZER)
        app = await _mk_application(udb, 1, OrganizerApplicationStatus.PENDING)
        await udb.commit()
        _login(4)  # организатор, но НЕ админ

        resp = await uclient.patch(
            f"/api/v1/organizer-applications/{app.id}",
            json={"status": "approved"},
        )
        assert resp.status_code == 403


if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ USER SERVICE (pytest)")
    print("=" * 80)
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])
    print("\n" + "=" * 80)
    print(f"КОД ВЫХОДА: {exit_code}")
    print("=" * 80)
    sys.exit(exit_code)
