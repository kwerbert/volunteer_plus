"""
Тесты Feed Service (оптимизировано: 7 → 4 теста без потери покрытия)
Требует: pip install pytest-asyncio
"""
import pytest
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================================
# 1. КОНФИГУРАЦИЯ И ЗАВИСИМОСТИ
# ============================================================================
class TestConfigAndSetup:
    def test_001_config_and_dependencies(self):
        """Проверка загрузки конфига и корректности зависимостей"""
        from app.services.feed_service.config import settings
        from app.services.feed_service.dependencies import get_db, get_settings
        import inspect

        assert settings.SERVICE_NAME == "feed_service"
        assert settings.SERVICE_PORT == 8001
        assert isinstance(settings.CACHE_ENABLED, bool)
        assert settings.CACHE_TTL_SECONDS > 0

        assert inspect.isasyncgenfunction(get_db)
        assert callable(get_settings)


# ============================================================================
# 2. СХЕМЫ И ВАЛИДАЦИЯ
# ============================================================================
class TestSchemas:
    def test_002_schema_validation_and_responses(self):
        """Проверка Pydantic валидации и сборки ответа"""
        from app.services.feed_service.api.schemas import (
            FeedFilterParams, FeedResponse, FeedSection,
            EventPreview, OrganizationPreview, FeedSectionType
        )
        from pydantic import ValidationError

        # Невалидные данные
        with pytest.raises(ValidationError): FeedFilterParams(location_lat=95.0)
        with pytest.raises(ValidationError): FeedFilterParams(page_size=100)
        with pytest.raises(ValidationError): FeedFilterParams(page=0)

        # Валидные данные
        params = FeedFilterParams(location_lat=55.75, location_lon=37.61, radius_km=10)
        assert params.page == 1

        # Сборка ответа
        org = OrganizationPreview(id=1, name="Test Org", logo_url=None, rating=4.5, verified=True, category_id=None)
        evt = EventPreview(
            id=100, title="Test Event", organization=org, description_preview="Desc",
            start_time=datetime.now(), end_time=datetime.now() + timedelta(hours=2),
            location_lat=55.75, location_lon=37.61
        )
        section = FeedSection(section_type=FeedSectionType.FROM_SUBSCRIPTIONS, section_title="Subs", events=[evt])
        feed = FeedResponse(user_id=1, generated_at=datetime.now(), filters_applied={}, sections=[section],
                            total_events=1, has_more=False)

        assert feed.model_dump()["user_id"] == 1
        assert len(feed.sections) == 1


# ============================================================================
# 3. КЭШ И ГЕОФИЛЬТРАЦИЯ
# ============================================================================
class TestCoreLogic:
    def test_003_cache_and_geofilter(self):
        """Проверка TTL-кэша и фильтрации по геолокации (Haversine)"""
        from app.services.feed_service.cache.cache_manager import CacheManager
        from app.services.feed_service.core.filter_engine import FilterEngine
        from app.services.feed_service.api.schemas import FeedFilterParams
        from app.services.feed_service.config import settings
        from app.services.feed_service.utils.geolocation import calculate_distance

        # Кэш
        cm = CacheManager(settings)
        assert cm.set("k1", {"v": 1}, ttl=1) is True
        assert cm.get("k1") == {"v": 1}
        time.sleep(1.1)
        assert cm.get("k1") is None

        # Геолокация
        fe = FilterEngine(settings)
        user_loc = {"lat": 55.7558, "lon": 37.6173}
        future = (datetime.now() + timedelta(days=1)).isoformat()

        events = [
            {"id": 1, "location_lat": 55.7600, "location_lon": 37.6200, "start_time": future},  # ~0.5 км
            {"id": 2, "location_lat": 59.9343, "location_lon": 30.3351, "start_time": future},  # СПб, ~630 км
            {"id": 3, "location_lat": None, "location_lon": None, "start_time": future}  # Без координат
        ]
        params = FeedFilterParams(location_lat=55.7558, location_lon=37.6173, radius_km=50)
        filtered = fe.filter_events(events, params, user_loc)
        ids = [e["id"] for e in filtered]

        assert 1 in ids  # Близкое прошло
        assert 2 not in ids  # Далёкое отфильтровано
        assert 3 in ids  # Без координат прошло
        assert calculate_distance(55.7558, 37.6173, 59.9343, 30.3351) > 600


# ============================================================================
# 4. АСИНХРОННЫЙ РЕПОЗИТОРИЙ
# ============================================================================
@pytest.mark.asyncio
class TestAsyncRepository:
    async def test_004_async_repo_logging(self):
        """Проверка async-репозитория и статистики"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.pool import StaticPool
        from app.services.feed_service.db.models import Base, FeedServiceLog
        from app.services.feed_service.db.repository import FeedRepository
        from app.services.feed_service.config import settings

        # In-memory async SQLite (StaticPool гарантирует одну БД в памяти)
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSession(engine) as session:
            repo = FeedRepository(session, settings)
            await repo.log_feed_generation(1, "req-1", 100, 10, True)
            await repo.log_feed_generation(2, "req-2", 200, 0, False, "Timeout")

            stats = await repo.get_recent_feed_stats(hours=1)
            assert stats["total_requests"] == 2
            assert stats["avg_processing_time_ms"] == 150.0
            assert stats["cache_hit_rate_percent"] == 50.0
            assert stats["error_rate_percent"] == 50.0

# pytest tests/test_feed_s.py -v