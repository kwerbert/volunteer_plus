# tests/test_analytics_s.py
"""
Тесты Analytics Service (pytest версия)
"""
import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ============================================================================
# ✅ КРИТИЧЕСКИ ВАЖНО: Очищаем кэш ДО любого импорта сервисов
# ============================================================================
def _clear_analytics_cache():
    """Принудительная очистка кэша настроек"""
    # Сначала удаляем модуль из кэша импортов если он там есть
    modules_to_clear = [
        'app.services.analytics_service.config',
        'app.services.analytics_service.main',
        'app.services.analytics_service.core.service',
        'app.services.analytics_service.db.session',
        'app.services.analytics_service.db.repository',
        'app.services.analytics_service.api.router',
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    # Теперь импортируем и очищаем кэш
    try:
        from app.services.analytics_service.config import get_settings
        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    # Выполняем очистку при загрузке модуля теста
    _clear_analytics_cache()

# ============================================================================
# FIXTURES
# ============================================================================
@pytest.fixture
def mock_repository():
    """Фикстура для мок-репозитория"""
    repo = AsyncMock()
    repo.get_user_stats = AsyncMock()
    repo.get_stats_by_organization = AsyncMock()
    repo.get_monthly_stats = AsyncMock()
    repo.create_or_update_stats = AsyncMock()
    repo.create_monthly_stats = AsyncMock()
    repo.update_preferred_roles = AsyncMock()
    return repo

@pytest.fixture
def mock_session():
    """Фикстура для мок-сессии БД"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars().all.return_value = []
    session.execute.return_value = mock_result
    return session

@pytest.fixture
def clear_analytics_settings_cache():
    """Очищает кэш настроек перед тестом и после"""
    from app.services.analytics_service.config import get_settings
    get_settings.cache_clear()
    # Также удаляем модуль main из кэша
    if 'app.services.analytics_service.main' in sys.modules:
        del sys.modules['app.services.analytics_service.main']
    yield
    get_settings.cache_clear()

# ============================================================================
# ТЕСТЫ КОНФИГУРАЦИИ
# ============================================================================
class TestConfig:
    """Тесты конфигурации сервиса"""
    def test_001_config_settings(self, clear_analytics_settings_cache):
        """Проверка загрузки настроек из конфигурации"""
        # Импортируем ПОСЛЕ очистки кэша
        from app.services.analytics_service.config import get_settings
        settings = get_settings()
        # Проверяем ключевые настройки
        assert settings.SERVICE_PORT == 8005, f"Порт должен быть 8005, получено {settings.SERVICE_PORT}"
        assert settings.SERVICE_NAME == "analytics_service", f"Имя сервиса неверное: {settings.SERVICE_NAME}"
        assert "sqlite+aiosqlite" in settings.DATABASE_URL, f"URL БД неверный: {settings.DATABASE_URL}"
        print("✓ Конфигурация загружена корректно")

# ============================================================================
# ТЕСТЫ СХЕМ (PYDANTIC)
# ============================================================================
class TestSchemas:
    """Тесты Pydantic схем"""
    def test_002_schemas_validation(self):
        """Проверка валидации основных схем"""
        from app.services.analytics_service.api.schemas import (
            UserStatsResponse,
            EventCompleteRequest
        )
        # Тест UserStatsResponse
        stats = UserStatsResponse(
            id=1,
            user_id=100,
            total_hours=50.5,
            total_events=10,
            organizations_count=3,
            created_at=datetime.now(timezone.utc)
        )
        assert stats.total_hours == 50.5
        assert stats.user_id == 100
        # Тест EventCompleteRequest
        request = EventCompleteRequest(
            user_id=100,
            hours_worked=4.0,
            role="volunteer"
        )
        assert request.hours_worked == 4.0
        assert request.role == "volunteer"
        print("✓ Pydantic схемы валидируются корректно")

# ============================================================================
# ТЕСТЫ БИЗНЕС-ЛОГИКИ (SERVICE)
# ============================================================================
@pytest.mark.asyncio
class TestService:
    """Тесты бизнес-логики"""
    async def test_003_user_analytics(self, mock_repository):
        """Проверка расчёта статистики пользователя"""
        from app.services.analytics_service.core.service import AnalyticsService
        # ✅ ИСПРАВЛЕНО: правильный импорт модели
        from app.services.analytics_service.db.models import VolunteerStats
        # Настраиваем мок-данные
        mock_repository.get_user_stats.return_value = VolunteerStats(
            id=1,
            user_id=100,
            hours_worked=20.0,
            events_completed=5,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc)
        )
        mock_repository.get_stats_by_organization.return_value = [
            {"organization_id": 1, "hours_worked": 20.0, "events_completed": 5}
        ]
        service = AnalyticsService(mock_repository)
        result = await service.get_user_analytics(100)
        assert result.total_hours == 20.0
        assert result.total_events == 5
        assert result.organizations_count == 1
        print("✓ Расчёт часов волонтёрства работает корректно")

    async def test_004_organization_analytics(self, mock_repository):
        """Проверка агрегации данных по организациям"""
        from app.services.analytics_service.core.service import AnalyticsService
        mock_repository.get_stats_by_organization.return_value = [
            {"organization_id": 1, "hours_worked": 10.0, "events_completed": 2, "role": "volunteer"},
            {"organization_id": 2, "hours_worked": 15.0, "events_completed": 3, "role": "coordinator"}
        ]
        service = AnalyticsService(mock_repository)
        # Мокаем HTTP-запрос к Organization Service
        service._get_organization_name = AsyncMock(return_value="Test Org")
        result = await service.get_organization_analytics(100)
        assert result.total_organizations == 2
        assert len(result.organizations) == 2
        print("✓ Агрегация данных по организациям работает корректно")

# ============================================================================
# ТЕСТЫ РЕПОЗИТОРИЯ
# ============================================================================
@pytest.mark.asyncio
class TestRepository:
    """Тесты репозитория"""
    async def test_005_repository_creation(self, mock_session):
        """Проверка создания репозитория"""
        from app.services.analytics_service.db.repository import AnalyticsRepository
        repo = AnalyticsRepository(mock_session)
        assert repo is not None
        assert repo.session == mock_session
        print("✓ Репозиторий создаётся корректно")

# ============================================================================
# ТЕСТЫ FASTAPI ПРИЛОЖЕНИЯ
# ============================================================================
class TestMainApp:
    """Тесты FastAPI приложения"""
    def test_006_app_and_health_endpoint(self, clear_analytics_settings_cache):
        """Проверка создания приложения и availability health endpoint"""
        import importlib
        # Очищаем кэш настроек перед импортом main модуля
        from app.services.analytics_service.config import get_settings
        get_settings.cache_clear()
        # Принудительно удаляем модуль из кэша если он там есть
        if 'app.services.analytics_service.main' in sys.modules:
            del sys.modules['app.services.analytics_service.main']
        # Импортируем main модуль заново
        main_module = importlib.import_module('app.services.analytics_service.main')
        app = main_module.app
        # Проверка приложения
        assert app is not None, "FastAPI app не создан"
        assert app.title == "analytics_service", f"Title неверный: {app.title}"
        # Проверка health endpoint (рекурсивно по вложенным роутерам)
        from tests.conftest import collect_route_paths
        routes = collect_route_paths(app)
        assert "/health" in routes, "Health endpoint отсутствует"
        assert "/" in routes, "Root endpoint отсутствует"
        print("✓ FastAPI приложение создано корректно")
        print("✓ Health endpoint доступен")

# ============================================================================
# ЗАПУСК ТЕСТОВ
# ============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ ANALYTICS SERVICE (pytest)")
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

# pytest tests/test_analytics_s.py -v