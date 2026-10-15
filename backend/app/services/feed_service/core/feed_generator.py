"""
Генератор персонализированной ленты.
✅ Исправлено: aiohttp.ClientSession внедряется через зависимости, нет утечек.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import aiohttp
import logging

from ..config import Settings
from ..db.repository import FeedRepository
from .filter_engine import FilterEngine
from .recommendation_engine import RecommendationEngine
from ..api.schemas import (
    FeedFilterParams, FeedResponse, FeedSection,
    FeedSectionType, EventPreview, OrganizationPreview
)

logger = logging.getLogger(__name__)


class FeedGenerator:
    def __init__(
        self,
        repository: FeedRepository,
        settings: Settings,
        http_session: aiohttp.ClientSession,  # <-- внедряемая сессия
    ):
        self.repository = repository
        self.settings = settings
        self.http_session = http_session  # ✅ Используем общую сессию
        self.filter_engine = FilterEngine(settings)
        self.recommendation_engine = RecommendationEngine(settings)

    async def generate_feed(
        self,
        user_id: int,
        filter_params: FeedFilterParams,
    ) -> FeedResponse:
        logger.info(f"Starting feed generation for user_id={user_id}")

        # Шаг 1: Получение данных о пользователе
        user_data = await self._get_user_data(user_id)
        user_location = {
            "lat": filter_params.location_lat or user_data.get("location_lat"),
            "lon": filter_params.location_lon or user_data.get("location_lon"),
        }

        # Шаг 2: Получение подписок пользователя
        subscriptions = await self._get_user_subscriptions(user_id)
        subscribed_org_ids = [sub["org_id"] for sub in subscriptions]
        logger.info(f"User {user_id} has {len(subscribed_org_ids)} subscriptions")

        # Шаг 3: Получение мероприятий + обогащение данными организаций
        all_events = await self._fetch_and_enrich_events(
            subscribed_org_ids=subscribed_org_ids,
            filter_params=filter_params,
            user_location=user_location,
        )

        # Шаг 4: Фильтрация
        filtered_events = self.filter_engine.filter_events(
            all_events, filter_params, user_location
        )

        # Шаг 5: Формирование секций
        sections = await self._build_sections(
            events=filtered_events,
            subscribed_org_ids=subscribed_org_ids,
            subscriptions=subscriptions,
            user_id=user_id,
            filter_params=filter_params,
            user_location=user_location,
        )

        # Шаг 6: Формирование ответа
        total_events = sum(len(section.events) for section in sections)
        feed = FeedResponse(
            user_id=user_id,
            generated_at=datetime.now(),
            filters_applied=filter_params.model_dump(),
            sections=sections,
            total_events=total_events,
            has_more=total_events >= filter_params.page_size,
        )

        logger.info(f"Feed generated: {total_events} events in {len(sections)} sections")
        return feed

    async def _get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получение данных о пользователе из User Service (service-to-service)."""
        try:
            async with self.http_session.get(
                    f"{self.settings.USER_SERVICE_URL}/api/v1/users/{user_id}/profile",
                    headers={"X-Service-Key": self.settings.SERVICE_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.warning(
                    f"User Service returned {response.status} for user {user_id}"
                )
        except Exception as e:
            logger.warning(f"Error fetching user {user_id}: {e}")

        return {
            "id": user_id,
            "location_lat": None,
            "location_lon": None,
            "settings": {
                "show_only_subscriptions": False,
                "search_radius_km": self.settings.DEFAULT_SEARCH_RADIUS_KM,
            },
        }

    async def _get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение подписок пользователя из Subscription Service"""
        try:
            params = {"user_id": user_id, "active_only": "true"}
            # ✅ Используем внедрённую сессию
            async with self.http_session.get(
                f"{self.settings.SUBSCRIPTION_SERVICE_URL}/api/v1/subscriptions",
                params=params,
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.warning(f"Error fetching subscriptions: {e}")
        return []

    async def _fetch_and_enrich_events(
        self,
        subscribed_org_ids: List[int],
        filter_params: FeedFilterParams,
        user_location: Dict[str, Optional[float]],
    ) -> List[Dict[str, Any]]:
        """
        Получение мероприятий из Event Service + обогащение данными организаций.
        ✅ КРИТИЧЕСКИ: нормализация полей даты (start_date → start_time).
        """
        try:
            params = {
                "date_from": filter_params.date_from.isoformat() if filter_params.date_from else None,
                "date_to": filter_params.date_to.isoformat() if filter_params.date_to else None,
                "page_size": filter_params.page_size * 3,
            }
            if subscribed_org_ids:
                params["org_ids"] = ",".join(map(str, subscribed_org_ids))  # было organization_ids

            # ✅ Используем внедрённую сессию
            async with self.http_session.get(
                f"{self.settings.EVENT_SERVICE_URL}/api/v1/events",
                params={k: v for k, v in params.items() if v is not None},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Нормализация структуры ответа
                    if isinstance(data, list):
                        events = data
                    elif isinstance(data, dict):
                        events = data.get("events", [])
                    else:
                        events = []

                    # ✅ Обогащение данными организаций + нормализация полей
                    enriched = await self._enrich_events_with_organization_data(events)
                    logger.info(f"Fetched {len(enriched)} enriched events")
                    return enriched
                else:
                    logger.warning(f"Event Service returned status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []

    async def _enrich_events_with_organization_data(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Обогащение мероприятий данными организаций из Organization Service.
        ✅ Нормализация: start_date → start_time, end_date → end_time.
        """
        if not events:
            return []

        # Собираем уникальные org_id
        org_ids = list(
            set(
                event.get("org_id") or event.get("organization_id")
                for event in events
                if event.get("org_id") or event.get("organization_id")
            )
        )
        if not org_ids:
            return self._normalize_events(events)

        # Параллельное получение данных организаций
        organizations = await self._fetch_organizations_batch(org_ids)
        org_map = {org["id"]: org for org in organizations}

        # Обогащение каждого мероприятия
        enriched = []
        for event in events:
            org_id = event.get("org_id") or event.get("organization_id")
            org_data = org_map.get(org_id, {}) if org_id else {}

            # Копируем event и добавляем нормализованные поля
            enriched_event = event.copy()

            # ✅ НОРМАЛИЗАЦИЯ ДАТ: поддержка обоих форматов
            if "start_date" in enriched_event and "start_time" not in enriched_event:
                enriched_event["start_time"] = enriched_event["start_date"]
            if "end_date" in enriched_event and "end_time" not in enriched_event:
                enriched_event["end_time"] = enriched_event.get("end_date")

            # Добавляем данные организации
            enriched_event["organization_id"] = org_id
            enriched_event["organization_name"] = org_data.get("name", "Организация")
            enriched_event["organization_logo"] = org_data.get("logo_url")
            enriched_event["organization_rating"] = org_data.get("rating", 0.0)
            enriched_event["organization_verified"] = org_data.get("is_verified", False)
            enriched_event["category_id"] = org_data.get("category_id")

            enriched.append(enriched_event)

        return enriched

    async def _fetch_organizations_batch(
        self,
        org_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """Параллельное получение данных организаций через общую сессию."""
        tasks = []
        for org_id in org_ids:
            task = self.http_session.get(
                f"{self.settings.ORGANIZATION_SERVICE_URL}/api/v1/organizations/{org_id}",
                timeout=aiohttp.ClientTimeout(total=2),
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        organizations = []

        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.warning(f"Error fetching org {org_ids[i]}: {response}")
                organizations.append(self._get_fallback_org(org_ids[i]))
                continue
            async with response:
                if response.status == 200:
                    org_data = await response.json()
                    organizations.append(org_data)
                else:
                    organizations.append(self._get_fallback_org(org_ids[i]))

        return organizations

    @staticmethod
    def _get_fallback_org(org_id: int) -> Dict[str, Any]:
        """Fallback данные для недоступной организации."""
        return {
            "id": org_id,
            "name": "Организация",
            "logo_url": None,
            "rating": 0.0,
            "is_verified": False,
            "category_id": None,
        }

    @staticmethod
    def _normalize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Нормализация полей даты в событиях без обогащения."""
        normalized = []
        for event in events:
            evt = event.copy()
            if "start_date" in evt and "start_time" not in evt:
                evt["start_time"] = evt["start_date"]
            if "end_date" in evt and "end_time" not in evt:
                evt["end_time"] = evt.get("end_date")
            normalized.append(evt)
        return normalized

    async def _build_sections(
        self,
        events: List[Dict[str, Any]],
        subscribed_org_ids: List[int],
        subscriptions: List[Dict[str, Any]],
        user_id: int,
        filter_params: FeedFilterParams,
        user_location: Dict[str, Optional[float]],
    ) -> List[FeedSection]:
        """Формирование секций ленты."""
        sections = []

        # Секция 1: От ваших организаций
        subscribed_events = [
            event for event in events
            if event.get("organization_id") in subscribed_org_ids
        ]
        if subscribed_events:
            subscribed_events_sorted = sorted(
                subscribed_events,
                key=lambda e: e.get("start_time", "") or e.get("start_date", ""),
            )
            sections.append(
                FeedSection(
                    section_type=FeedSectionType.FROM_SUBSCRIPTIONS,
                    section_title="От ваших организаций",
                    events=[
                        self._build_event_preview(event)
                        for event in subscribed_events_sorted[: filter_params.page_size]
                    ],
                    layout="horizontal",
                )
            )

        # Секция 2: Рекомендации (если не только подписки)
        if not filter_params.show_only_subscriptions:
            recommendations = await self.recommendation_engine.get_recommendations(
                user_id=user_id,
                exclude_org_ids=subscribed_org_ids,
                filter_params=filter_params,
                user_location=user_location,
            )
            if recommendations:
                sections.append(
                    FeedSection(
                        section_type=FeedSectionType.RECOMMENDATIONS,
                        section_title="Рекомендации для вас",
                        events=recommendations,
                        layout="vertical",
                    )
                )

        return sections

    @staticmethod
    def _build_event_preview(event: Dict[str, Any]) -> EventPreview:
        """
        Построение EventPreview из словаря.
        ✅ Безопасное получение полей с поддержкой обоих форматов дат.
        """
        # ✅ Получение времени начала: пробуем start_time, затем start_date
        start_time_val = event.get("start_time") or event.get("start_date")
        end_time_val = (
            event.get("end_time") or event.get("end_date") or start_time_val
        )

        # Парсинг дат если они в строковом формате
        if isinstance(start_time_val, str):
            try:
                start_time = datetime.fromisoformat(start_time_val.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                start_time = datetime.now()
        elif isinstance(start_time_val, datetime):
            start_time = start_time_val
        else:
            start_time = datetime.now()

        if isinstance(end_time_val, str):
            try:
                end_time = datetime.fromisoformat(end_time_val.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                end_time = start_time
        elif isinstance(end_time_val, datetime):
            end_time = end_time_val
        else:
            end_time = start_time

        return EventPreview(
            id=event.get("id", 0),
            title=event.get("title", "Без названия"),
            organization=OrganizationPreview(
                id=event.get("organization_id", 0),
                name=event.get("organization_name", "Организация"),
                logo_url=event.get("organization_logo"),
                rating=float(event.get("organization_rating", 0.0)),
                verified=bool(event.get("organization_verified", False)),
                category_id=event.get("category_id"),
            ),
            description_preview=(
                event.get("description", "")[:100] if event.get("description") else None
            ),
            start_time=start_time,
            end_time=end_time,
            location_lat=event.get("location_lat"),
            location_lon=event.get("location_lon"),
            distance_km=event.get("distance_km"),
            required_role_id=event.get("required_role_id"),
            max_participants=event.get("max_participants"),
            registered_count=event.get("registered_count", 0),
        )