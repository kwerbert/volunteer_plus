import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _clear_analytics_cache():
    modules_to_clear = [
        "app.services.analytics_service.config",
        "app.services.analytics_service.main",
        "app.services.analytics_service.core.service",
        "app.services.analytics_service.db.session",
        "app.services.analytics_service.db.repository",
        "app.services.analytics_service.api.router",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    try:
        from app.services.analytics_service.config import get_settings

        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    _clear_analytics_cache()


@pytest.fixture
def mock_repository():
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
    from app.services.analytics_service.config import get_settings

    get_settings.cache_clear()
    if "app.services.analytics_service.main" in sys.modules:
        del sys.modules["app.services.analytics_service.main"]
    yield
    get_settings.cache_clear()


class TestConfig:
    def test_001_config_settings(self, clear_analytics_settings_cache):
        from app.services.analytics_service.config import get_settings

        settings = get_settings()
        assert settings.SERVICE_PORT == 8005, (
            f"Порт должен быть 8005, получено {settings.SERVICE_PORT}"
        )
        assert settings.SERVICE_NAME == "analytics_service", (
            f"Имя сервиса неверное: {settings.SERVICE_NAME}"
        )
        assert "sqlite+aiosqlite" in settings.DATABASE_URL, (
            f"URL БД неверный: {settings.DATABASE_URL}"
        )
        print("Конфигурация загружена корректно")


class TestSchemas:
    def test_002_schemas_validation(self):
        from app.services.analytics_service.api.schemas import (
            EventCompleteRequest,
            UserStatsResponse,
        )

        stats = UserStatsResponse(
            id=1,
            user_id=100,
            total_hours=50.5,
            total_events=10,
            organizations_count=3,
            created_at=datetime.now(timezone.utc),
        )
        assert stats.total_hours == 50.5
        assert stats.user_id == 100
        request = EventCompleteRequest(user_id=100, hours_worked=4.0, role="volunteer")
        assert request.hours_worked == 4.0
        assert request.role == "volunteer"
        print("Pydantic схемы валидируются корректно")


@pytest.mark.asyncio
class TestService:
    async def test_003_user_analytics(self, mock_repository):
        from app.services.analytics_service.core.service import AnalyticsService
        from app.services.analytics_service.db.models import VolunteerStats

        mock_repository.get_user_stats.return_value = VolunteerStats(
            id=1,
            user_id=100,
            hours_worked=20.0,
            events_completed=5,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
        )
        mock_repository.get_stats_by_organization.return_value = [
            {"organization_id": 1, "hours_worked": 20.0, "events_completed": 5}
        ]
        service = AnalyticsService(mock_repository)
        result = await service.get_user_analytics(100)
        assert result.total_hours == 20.0
        assert result.total_events == 5
        assert result.organizations_count == 1
        print("Расчёт часов волонтёрства работает корректно")

    async def test_004_organization_analytics(self, mock_repository):
        from app.services.analytics_service.core.service import AnalyticsService

        mock_repository.get_stats_by_organization.return_value = [
            {
                "organization_id": 1,
                "hours_worked": 10.0,
                "events_completed": 2,
                "role": "volunteer",
            },
            {
                "organization_id": 2,
                "hours_worked": 15.0,
                "events_completed": 3,
                "role": "coordinator",
            },
        ]
        service = AnalyticsService(mock_repository)
        service._get_organization_name = AsyncMock(return_value="Test Org")
        result = await service.get_organization_analytics(100)
        assert result.total_organizations == 2
        assert len(result.organizations) == 2
        print("Агрегация данных по организациям работает корректно")


@pytest.mark.asyncio
class TestRepository:
    async def test_005_repository_creation(self, mock_session):
        from app.services.analytics_service.db.repository import AnalyticsRepository

        repo = AnalyticsRepository(mock_session)
        assert repo is not None
        assert repo.session == mock_session
        print("Репозиторий создаётся корректно")


class TestMainApp:
    def test_006_app_and_health_endpoint(self, clear_analytics_settings_cache):
        import importlib

        from app.services.analytics_service.config import get_settings

        get_settings.cache_clear()
        if "app.services.analytics_service.main" in sys.modules:
            del sys.modules["app.services.analytics_service.main"]
        main_module = importlib.import_module("app.services.analytics_service.main")
        app = main_module.app
        assert app is not None, "FastAPI app не создан"
        assert app.title == "analytics_service", f"Title неверный: {app.title}"
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)
        assert "/health" in routes, "Health endpoint отсутствует"
        assert "/" in routes, "Root endpoint отсутствует"
        print("FastAPI приложение создано корректно")
        print("Health endpoint доступен")


if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ ANALYTICS SERVICE (pytest)")
    print("=" * 80)
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])
    print("\n" + "=" * 80)
    print(f"КОД ВЫХОДА: {exit_code}")
    print("=" * 80)
    sys.exit(exit_code)
