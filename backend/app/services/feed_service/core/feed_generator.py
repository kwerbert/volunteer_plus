import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from ..api.schemas import (
    EventPreview,
    FeedFilterParams,
    FeedResponse,
    FeedSection,
    FeedSectionType,
)
from ..config import Settings
from ..db.repository import FeedRepository
from .event_preview import build_event_preview, normalize_event_dates
from .filter_engine import FilterEngine
from .recommendation_engine import RecommendationEngine

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
        self.http_session = http_session  # Используем общую сессию
        self.filter_engine = FilterEngine(settings)
        self.recommendation_engine = RecommendationEngine(settings)

    async def generate_feed(
        self,
        user_id: int,
        filter_params: FeedFilterParams,
    ) -> FeedResponse:
        logger.info(f"Starting feed generation for user_id={user_id}")

        # Шаг 1: Данные пользователя (role нужна для секции MY_EVENTS)
        user_data = await self._get_user_data(user_id)
        is_organizer = str(user_data.get("role") or "").lower() == "organizer"
        user_location = {
            "lat": filter_params.location_lat or user_data.get("location_lat"),
            "lon": filter_params.location_lon or user_data.get("location_lon"),
        }

        # Шаг 2: Подписки пользователя
        subscriptions = await self._get_user_subscriptions(user_id)
        subscribed_org_ids = [sub["org_id"] for sub in subscriptions]
        logger.info(f"User {user_id} has {len(subscribed_org_ids)} subscriptions")

        # Источник правды — organization_organizers (organization_service).
        my_org_ids = await self._get_my_org_ids(user_id) if is_organizer else []
        if my_org_ids:
            logger.info(
                "User %s organizes %s orgs: %s", user_id, len(my_org_ids), my_org_ids
            )

        # Шаг 3: Мероприятия. Общие и «мои» — независимые запросы, параллельно.
        all_events, my_events = await asyncio.gather(
            self._fetch_and_enrich_events(
                subscribed_org_ids=subscribed_org_ids,
                filter_params=filter_params,
                user_location=user_location,
            ),
            self._fetch_my_events(my_org_ids),
        )

        # Шаг 4: Фильтрация — только общая лента. «Мои мероприятия» —
        # управленческая секция организатора, волонтёрские фильтры
        # (радиус/категории/даты) к ней не применяются.
        filtered_events = self.filter_engine.filter_events(
            all_events, filter_params, user_location
        )

        # Шаг 5: Секции
        sections = await self._build_sections(
            events=filtered_events,
            subscribed_org_ids=subscribed_org_ids,
            subscriptions=subscriptions,
            user_id=user_id,
            filter_params=filter_params,
            user_location=user_location,
            my_events=my_events,
            my_org_ids=my_org_ids,
        )

        # Шаг 6: Ответ
        total_events = sum(len(section.events) for section in sections)
        feed = FeedResponse(
            user_id=user_id,
            generated_at=datetime.now(),
            filters_applied=filter_params.model_dump(),
            sections=sections,
            total_events=total_events,
            has_more=total_events >= filter_params.page_size,
        )
        logger.info(
            f"Feed generated: {total_events} events in {len(sections)} sections"
        )
        return feed

    async def _get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Данные пользователя из User Service (service-to-service).
        /users/{id}/profile отдаёт вложенную структуру {user, settings, location} —
        нормализуем в плоский вид"""
        try:
            async with self.http_session.get(
                f"{self.settings.USER_SERVICE_URL}/api/v1/users/{user_id}/profile",
                headers={"X-Service-Key": self.settings.SERVICE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status == 200:
                    return self._normalize_user_data(await response.json(), user_id)
                logger.warning(
                    f"User Service returned {response.status} for user {user_id}"
                )
        except Exception as e:
            logger.warning(f"Error fetching user {user_id}: {e}")
        return self._fallback_user_data(user_id)

    def _normalize_user_data(
        self, data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Поддерживает вложенный (/profile) и плоский (/feed-profile) форматы."""
        user = data.get("user") or data
        location = data.get("location") or {}
        settings = data.get("settings") or user.get("settings") or {}
        lat = user.get("location_lat")
        lon = user.get("location_lon")
        if lat is None:
            lat = location.get("latitude")
        if lon is None:
            lon = location.get("longitude")
        return {
            "id": user.get("id") or user.get("user_id") or user_id,
            "role": str(user.get("role") or "volunteer").lower(),
            "location_lat": lat,
            "location_lon": lon,
            "settings": settings
            or {
                "show_only_subscriptions": False,
                "search_radius_km": self.settings.DEFAULT_SEARCH_RADIUS_KM,
            },
        }

    def _fallback_user_data(self, user_id: int) -> Dict[str, Any]:
        """User Service недоступен → обычный волонтёр без секции MY_EVENTS.
        Лента должна работать и без него (graceful degradation)."""
        return {
            "id": user_id,
            "role": "volunteer",
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

    async def _get_my_org_ids(self, user_id: int) -> List[int]:
        """Организации, где пользователь — активный организатор.
        Единый источник правды — organization_organizers (organization_service).
        Сбой сервиса → [] → секции MY_EVENTS не будет, лента не падает."""
        try:
            async with self.http_session.get(
                f"{self.settings.ORGANIZATION_SERVICE_URL}"
                f"/internal/users/{user_id}/organizations",
                headers={"X-Service-Key": self.settings.SERVICE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return sorted({int(org_id) for org_id in data})
                logger.warning(
                    "Organization Service user-orgs/%s: HTTP %s",
                    user_id,
                    response.status,
                )
        except Exception as e:
            logger.warning(f"Error fetching organizer orgs of user {user_id}: {e}")
        return []

    async def _fetch_my_events(self, my_org_ids: List[int]) -> List[Dict[str, Any]]:
        if not my_org_ids:
            return []
        try:
            params = {
                "org_ids": ",".join(map(str, my_org_ids)),
                "status": "all",
            }
            async with self.http_session.get(
                f"{self.settings.EVENT_SERVICE_URL}/api/v1/events",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        events = data
                    elif isinstance(data, dict):
                        events = data.get("events", [])
                    else:
                        events = []
                    return await self._enrich_events_with_organization_data(events)
                logger.warning(
                    f"Event Service (my events) returned status {response.status}"
                )
        except Exception as e:
            logger.error(f"Error fetching my events: {e}")
        return []

    async def _fetch_and_enrich_events(
        self,
        subscribed_org_ids: List[int],
        filter_params: FeedFilterParams,
        user_location: Dict[str, Optional[float]],
    ) -> List[Dict[str, Any]]:
        """
        Получение мероприятий из Event Service + обогащение данными организаций.
        КРИТИЧЕСКИ: нормализация полей даты (start_date → start_time).
        """
        try:
            params = {
                "date_from": filter_params.date_from.isoformat()
                if filter_params.date_from
                else None,
                "date_to": filter_params.date_to.isoformat()
                if filter_params.date_to
                else None,
                "page_size": filter_params.page_size * 3,
            }
            if subscribed_org_ids:
                params["org_ids"] = ",".join(map(str, subscribed_org_ids))

            async with self.http_session.get(
                f"{self.settings.EVENT_SERVICE_URL}/api/v1/events",
                params={k: v for k, v in params.items() if v is not None},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        events = data
                    elif isinstance(data, dict):
                        events = data.get("events", [])
                    else:
                        events = []
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
        Нормализация: start_date → start_time, end_date → end_time.
        """
        if not events:
            return []

        org_ids = list(
            set(
                event.get("org_id") or event.get("organization_id")
                for event in events
                if event.get("org_id") or event.get("organization_id")
            )
        )
        if not org_ids:
            return self._normalize_events(events)

        organizations = await self._fetch_organizations_batch(org_ids)
        org_map = {org["id"]: org for org in organizations}

        enriched = []
        for event in events:
            org_id = event.get("org_id") or event.get("organization_id")
            org_data = org_map.get(org_id, {}) if org_id else {}

            enriched_event = normalize_event_dates(event)
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
        return [normalize_event_dates(event) for event in events]

    async def _build_sections(
        self,
        events: List[Dict[str, Any]],
        subscribed_org_ids: List[int],
        subscriptions: List[Dict[str, Any]],
        user_id: int,
        filter_params: FeedFilterParams,
        user_location: Dict[str, Optional[float]],
        my_events: Optional[List[Dict[str, Any]]] = None,
        my_org_ids: Optional[List[int]] = None,
    ) -> List[FeedSection]:
        """Формирование секций ленты."""
        sections: List[FeedSection] = []
        my_events = my_events or []
        my_org_ids = my_org_ids or []
        if my_events:
            ordered = self._sort_my_events(my_events)
            sections.append(
                FeedSection(
                    section_type=FeedSectionType.MY_EVENTS,
                    section_title="Мои мероприятия",
                    events=[
                        self._build_event_preview(event)
                        for event in ordered[: filter_params.page_size]
                    ],
                    layout="vertical",
                )
            )

        # Секция 1: От ваших организаций
        subscribed_events = [
            event
            for event in events
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

        # Секция 2: Рекомендации (если не только подписки).
        # Организатор тоже видит рекомендации — мероприятия ДРУГИХ
        # организаций «для вдохновения». Свои орг исключаем: они в MY_EVENTS.
        if not filter_params.show_only_subscriptions:
            exclude_org_ids = sorted(set(subscribed_org_ids) | set(my_org_ids))
            recommendations = await self.recommendation_engine.get_recommendations(
                user_id=user_id,
                exclude_org_ids=exclude_org_ids,
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
    def _sort_my_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def start_key(e: Dict[str, Any]) -> str:
            return e.get("start_time") or e.get("start_date") or ""

        active = [e for e in events if (e.get("status") or "active") == "active"]
        completed = [e for e in events if e.get("status") == "completed"]
        cancelled = [e for e in events if e.get("status") == "cancelled"]

        active.sort(key=start_key)
        completed.sort(key=start_key, reverse=True)
        cancelled.sort(
            key=lambda e: e.get("cancelled_at") or start_key(e), reverse=True
        )
        return active + completed + cancelled

    @staticmethod
    def _build_event_preview(event: Dict[str, Any]) -> EventPreview:
        return build_event_preview(event)
