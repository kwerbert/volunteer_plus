"""
Тесты Subscription Service (pytest версия)
Консервативный перевод с unittest → pytest
"""
import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================================
# КРИТИЧЕСКИ ВАЖНО: Настройка путей (как в оригинальных тестах)
# ============================================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
    # ИСПРАВЛЕНО: session.add() — синхронный метод, нужен MagicMock, не AsyncMock
    session.add = MagicMock()
    return session

@pytest.fixture
def mock_repository():
    """Фикстура для мок-репозитория"""
    repo = AsyncMock()
    repo.get_by_user = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_user_and_org = AsyncMock()
    repo.create = AsyncMock()
    repo.soft_delete = AsyncMock()
    repo.update_role = AsyncMock()
    repo.log_action = AsyncMock()
    return repo

@pytest.fixture
def clear_settings_cache():
    """Очистка кэша настроек"""
    from app.services.subscription_service.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

# ============================================================================
# ТЕСТЫ КОНФИГУРАЦИИ
# ============================================================================
class TestConfig:
    """Тесты конфигурации сервиса"""
    def test_001_config_settings(self, clear_settings_cache):
        """Проверка основных настроек сервиса"""
        from app.services.subscription_service.config import settings
        assert settings.SERVICE_PORT == 8002
        assert settings.SERVICE_NAME == "subscription_service"
        assert settings.DATABASE_URL.endswith("volunteer_plus.db")
        assert "sqlite+aiosqlite" in settings.DATABASE_URL

    def test_002_config_singleton(self):
        """Проверка что settings кэшируется (singleton)"""
        from app.services.subscription_service.config import get_settings
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

# ============================================================================
# ТЕСТЫ СХЕМ
# ============================================================================
class TestSchemas:
    """Тесты Pydantic схем"""
    def test_003_subscription_create_schema(self):
        """Проверка схемы создания подписки"""
        from app.services.subscription_service.api.schemas import SubscriptionCreate
        from pydantic import ValidationError
        # Валидные данные
        sub = SubscriptionCreate(user_id=1, org_id=2, role="volunteer")
        assert sub.user_id == 1
        assert sub.org_id == 2
        assert sub.role == "volunteer"
        # Role по умолчанию
        sub_default = SubscriptionCreate(user_id=1, org_id=2)
        assert sub_default.role == "volunteer"
        # Невалидные данные
        with pytest.raises(ValidationError):
            SubscriptionCreate(user_id="invalid", org_id=2)

    def test_004_subscription_update_schema(self):
        """Проверка схемы обновления подписки"""
        from app.services.subscription_service.api.schemas import SubscriptionUpdate
        update_role = SubscriptionUpdate(role="admin")
        assert update_role.role == "admin"
        assert update_role.active is None
        update_active = SubscriptionUpdate(active=False)
        assert update_active.active is False
        assert update_active.role is None

    def test_005_response_schemas(self):
        """Проверка схем ответов API"""
        from app.services.subscription_service.api.schemas import (
            SubscriptionResponse,
            SubscriptionCheckResponse,
            MessageResponse
        )
        response = SubscriptionResponse(
            id=1, user_id=100, org_id=200, role="volunteer",
            active=True, created_at=datetime.now(timezone.utc)
        )
        assert response.id == 1
        assert response.active is True
        check_active = SubscriptionCheckResponse(
            is_subscribed=True, subscription_id=5, active=True, role="admin"
        )
        assert check_active.is_subscribed is True
        msg = MessageResponse(message="Success", detail="Info")
        assert msg.message == "Success"

# ============================================================================
# ТЕСТЫ МОДЕЛЕЙ
# ============================================================================

class TestModels:
    """Тесты SQLAlchemy моделей"""
    def test_006_subscription_model(self):
        """Проверка модели Subscription"""
        from app.services.subscription_service.db.models import Subscription
        assert Subscription.__tablename__ == "subscriptions"
        columns = [col.name for col in Subscription.__table__.columns]
        required_fields = ['id', 'user_id', 'org_id', 'role', 'active', 'created_at', 'updated_at']
        for field in required_fields:
            assert field in columns

    def test_007_subscription_log_model(self):
        """Проверка модели SubscriptionLog"""
        from app.services.subscription_service.db.models import SubscriptionLog
        assert SubscriptionLog.__tablename__ == "subscription_logs"
        columns = [col.name for col in SubscriptionLog.__table__.columns]
        required_fields = ['id', 'subscription_id', 'user_id', 'org_id', 'action', 'details', 'created_at']
        for field in required_fields:
            assert field in columns

# ============================================================================
# ТЕСТЫ РЕПОЗИТОРИЯ
# ============================================================================

@pytest.mark.asyncio
class TestRepository:
    """Тесты репозитория"""
    async def test_008_repository_read_operations(self, mock_session):
        """Проверка операций чтения"""
        from app.services.subscription_service.db.repository import SubscriptionRepository
        from app.services.subscription_service.db.models import Subscription
        repo = SubscriptionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [
            Subscription(id=1, user_id=100, org_id=200, role="volunteer", active=True),
            Subscription(id=2, user_id=100, org_id=201, role="admin", active=True)
        ]
        mock_result.scalar_one_or_none.return_value = Subscription(
            id=1, user_id=100, org_id=200, role="volunteer", active=True
        )
        mock_session.execute.return_value = mock_result
        result = await repo.get_by_user(user_id=100, active_only=True)
        assert len(result) == 2
        result = await repo.get_by_id(sub_id=1)
        assert result is not None

    async def test_009_repository_create(self, mock_session):
        """Проверка создания подписки"""
        from app.services.subscription_service.db.repository import SubscriptionRepository
        repo = SubscriptionRepository(mock_session)
        result = await repo.create(user_id=100, org_id=200, role="admin")
        assert result.user_id == 100
        assert result.org_id == 200
        mock_session.add.assert_called_once()

    async def test_010_repository_update_and_delete(self, mock_session):
        """Проверка обновления и удаления"""
        from app.services.subscription_service.db.repository import SubscriptionRepository
        repo = SubscriptionRepository(mock_session)
        result = await repo.soft_delete(sub_id=5)
        assert result is True
        mock_session.reset_mock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=5, user_id=100, org_id=200, role="admin", active=False
        )
        mock_session.execute.return_value = mock_result
        result = await repo.update_role(sub_id=5, role="admin", active=False)
        assert result is not None

    async def test_011_repository_log_action(self, mock_session):
        """Проверка логирования действий"""
        from app.services.subscription_service.db.repository import SubscriptionRepository
        from app.services.subscription_service.db.models import SubscriptionLog
        repo = SubscriptionRepository(mock_session)
        await repo.log_action(
            user_id=100, org_id=200, action="SUBSCRIBE",
            sub_id=5, details="Test subscription"
        )
        mock_session.add.assert_called_once()
        call_args = mock_session.add.call_args[0][0]
        assert isinstance(call_args, SubscriptionLog)
        assert call_args.user_id == 100

# ============================================================================
# ТЕСТЫ БИЗНЕС-ЛОГИКИ
# ============================================================================

@pytest.mark.asyncio
class TestService:
    """Тесты бизнес-логики"""
    async def test_012_service_subscribe_scenarios(self, mock_repository):
        """Проверка сценариев подписки (новая, дубликат, реактивация)"""
        from app.services.subscription_service.core.service import SubscriptionService
        from app.services.subscription_service.db.models import Subscription
        service = SubscriptionService(mock_repository)
        # Сценарий 1: Новая подписка
        mock_repository.get_by_user_and_org.return_value = None
        mock_repository.create.return_value = Subscription(
            id=1, user_id=100, org_id=200, role="volunteer", active=True
        )
        with patch('app.services.subscription_service.core.service.verify_user', return_value=True):
            with patch('app.services.subscription_service.core.service.verify_organization', return_value=True):
                result = await service.subscribe(user_id=100, org_id=200, role="volunteer")
                assert result is not None
                mock_repository.create.assert_called_once()
        # Сценарий 2: Уже активная подписка (ошибка)
        mock_repository.reset_mock()
        mock_repository.get_by_user_and_org.return_value = Subscription(
            id=1, user_id=100, org_id=200, role="volunteer", active=True
        )
        with pytest.raises(ValueError, match="already subscribed"):
            with patch('app.services.subscription_service.core.service.verify_user', return_value=True):
                with patch('app.services.subscription_service.core.service.verify_organization', return_value=True):
                    await service.subscribe(user_id=100, org_id=200, role="volunteer")

    async def test_013_service_subscribe_validation(self, mock_repository):
        """Проверка валидации пользователя и организации"""
        from app.services.subscription_service.core.service import SubscriptionService
        service = SubscriptionService(mock_repository)
        with pytest.raises(ValueError, match="User with ID 999 does not exist"):
            with patch('app.services.subscription_service.core.service.verify_user', return_value=False):
                await service.subscribe(user_id=999, org_id=200, role="volunteer")
        with pytest.raises(ValueError, match="Organization with ID 999 does not exist"):
            with patch('app.services.subscription_service.core.service.verify_user', return_value=True):
                with patch('app.services.subscription_service.core.service.verify_organization', return_value=False):
                    await service.subscribe(user_id=100, org_id=999, role="volunteer")

    async def test_014_service_unsubscribe(self, mock_repository):
        """Проверка отписки"""
        from app.services.subscription_service.core.service import SubscriptionService
        from app.services.subscription_service.db.models import Subscription
        service = SubscriptionService(mock_repository)
        mock_repository.get_by_id.return_value = Subscription(
            id=5, user_id=100, org_id=200, role="volunteer", active=True
        )
        mock_repository.soft_delete.return_value = True
        result = await service.unsubscribe(sub_id=5)
        assert result is True
        mock_repository.reset_mock()
        mock_repository.get_by_id.return_value = None
        result = await service.unsubscribe(sub_id=999)
        assert result is False

    async def test_015_service_update_and_check_status(self, mock_repository):
        """Проверка обновления и проверки статуса"""
        from app.services.subscription_service.core.service import SubscriptionService
        from app.services.subscription_service.api.schemas import SubscriptionUpdate
        from app.services.subscription_service.db.models import Subscription
        service = SubscriptionService(mock_repository)
        mock_repository.get_by_id.side_effect = [
            Subscription(id=5, user_id=100, org_id=200, role="volunteer", active=True),
            Subscription(id=5, user_id=100, org_id=200, role="admin", active=False)
        ]
        mock_repository.update_role.return_value = Subscription(
            id=5, user_id=100, org_id=200, role="admin", active=False
        )
        update_data = SubscriptionUpdate(role="admin", active=False)
        result = await service.update_subscription(5, update_data)
        assert result is not None
        mock_repository.reset_mock()
        mock_repository.get_by_user_and_org.return_value = Subscription(
            id=5, user_id=100, org_id=200, role="admin", active=True
        )
        result = await service.check_status(user_id=100, org_id=200)
        assert result.is_subscribed is True
        assert result.subscription_id == 5

    async def test_016_service_get_user_subscriptions(self, mock_repository):
        """Проверка получения всех подписок пользователя"""
        from app.services.subscription_service.core.service import SubscriptionService
        from app.services.subscription_service.db.models import Subscription
        service = SubscriptionService(mock_repository)
        mock_repository.get_by_user.return_value = [
            Subscription(id=1, user_id=100, org_id=200, role="volunteer", active=True),
            Subscription(id=2, user_id=100, org_id=201, role="admin", active=True)
        ]
        result = await service.get_user_subscriptions(user_id=100, active_only=True)
        assert len(result) == 2

# ============================================================================
# ТЕСТЫ HTTP КЛИЕНТА
# ============================================================================
@pytest.mark.asyncio
class TestHTTPClient:
    """Тесты HTTP клиента"""

    async def test_017_http_client_success(self):
        """Проверка верификации сущностей (успех)"""
        from app.services.subscription_service.utils.http_client import (
            verify_organization, verify_user
        )
        mock_response = AsyncMock()
        mock_response.status = 200
        # Настраиваем json() как AsyncMock с конкретным словарём
        mock_response.json = AsyncMock(
            return_value={"exists": True, "is_active": True}
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await verify_organization(org_id=200)
            assert result is True
            result = await verify_user(user_id=100)
            assert result is True

    async def test_018_http_client_errors(self):
        """Проверка обработки ошибок HTTP клиента"""
        from app.services.subscription_service.utils.http_client import verify_organization, verify_user
        mock_response_404 = AsyncMock()
        mock_response_404.status = 404
        mock_response_404.__aenter__ = AsyncMock(return_value=mock_response_404)
        mock_response_404.__aexit__ = AsyncMock(return_value=None)
        mock_session_404 = AsyncMock()
        mock_session_404.get = MagicMock(return_value=mock_response_404)
        mock_session_404.__aenter__ = AsyncMock(return_value=mock_session_404)
        mock_session_404.__aexit__ = AsyncMock(return_value=None)
        with patch('aiohttp.ClientSession', return_value=mock_session_404):
            result = await verify_organization(org_id=999)
            assert result is False

    async def test_019_http_client_connection_error(self):
        """Проверка ошибки соединения"""
        from app.services.subscription_service.utils.http_client import verify_user
        mock_session_error = AsyncMock()
        mock_session_error.get = MagicMock(side_effect=Exception("Connection error"))
        mock_session_error.__aenter__ = AsyncMock(return_value=mock_session_error)
        mock_session_error.__aexit__ = AsyncMock(return_value=None)
        with patch('aiohttp.ClientSession', return_value=mock_session_error):
            result = await verify_user(user_id=100)
            assert result is False

# ============================================================================
# ТЕСТЫ FASTAPI ПРИЛОЖЕНИЯ
# ============================================================================
class TestMainApp:
    """Тесты FastAPI приложения"""
    def test_020_app_creation(self, clear_settings_cache):
        """Проверка создания FastAPI приложения"""
        from app.services.subscription_service.main import app
        assert app is not None
        assert app.title == "subscription_service"
        assert app.version == "1.0.0"

    def test_021_app_routes(self, clear_settings_cache):
        """Проверка подключенных роутов (рекурсивно)"""
        from app.services.subscription_service.main import app
        from tests.conftest import collect_route_paths
        routes = collect_route_paths(app)
        subscription_routes = [r for r in routes if "subscription" in r.lower()]
        assert len(subscription_routes) > 0, (
            f"Не найдено ни одного роута subscriptions. Все пути: {routes}"
        )
        assert "/health" in routes

# ============================================================================
# ЗАПУСК ТЕСТОВ
# ============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ SUBSCRIPTION SERVICE (pytest)")
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

# pytest tests/test_subs_s.py -v
