"""
Рекомендательная система
Генерирует рекомендации мероприятий на основе поведения пользователя
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import aiohttp
import logging

from ..config import Settings
from ..api.schemas import FeedFilterParams, EventPreview, OrganizationPreview

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Класс для генерации рекомендаций мероприятий"""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_recommendations(
            self,
            user_id: int,
            exclude_org_ids: List[int],
            filter_params: FeedFilterParams,
            user_location: Dict[str, Optional[float]]
    ) -> List[EventPreview]:
        recommendations: List[EventPreview] = []
        try:
            preferred_roles = await self._get_user_preferred_roles(user_id)
            popular_events = await self._fetch_popular_events(
                exclude_org_ids=exclude_org_ids,
                preferred_roles=preferred_roles,
                filter_params=filter_params
            )

            for event in popular_events[:5]:
                # Поддержка обоих форматов: org_id из Event Service и organization_id
                org_id = event.get("organization_id") or event.get("org_id")

                # Нормализация даты (на случай если Event Service вернул start_date)
                start_time = event.get("start_time") or event.get("start_date")
                end_time = event.get("end_time") or event.get("end_date") or start_time

                if isinstance(start_time, str):
                    try:
                        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        start_time = datetime.now()
                if isinstance(end_time, str):
                    try:
                        end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        end_time = start_time

                recommendations.append(EventPreview(
                    id=event.get("id", 0),
                    title=event.get("title", "Без названия"),
                    organization=OrganizationPreview(
                        id=org_id or 0,
                        name=event.get("organization_name", "Организация"),
                        logo_url=event.get("organization_logo"),
                        rating=float(event.get("organization_rating", 0.0)),
                        verified=bool(event.get("organization_verified", False)),
                        category_id=event.get("category_id"),
                    ),
                    description_preview=(
                        event.get("description", "")[:100]
                        if event.get("description") else None
                    ),
                    start_time=start_time,
                    end_time=end_time,
                    location_lat=event.get("location_lat"),
                    location_lon=event.get("location_lon"),
                    distance_km=event.get("distance_km"),
                    required_role_id=event.get("required_role_id"),
                    max_participants=event.get("max_participants"),
                    registered_count=event.get("registered_count", 0),
                ))

            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)

        return recommendations

    async def _get_user_preferred_roles(self, user_id: int) -> List[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        f"{self.settings.ANALYTICS_SERVICE_URL}/api/v1/analytics/users/{user_id}/preferred-roles"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # analytics возвращает список объектов с полем "role"
                        roles = [item["role"] for item in data.get("roles", [])]
                        return roles
        except Exception:
            return []

    async def _fetch_popular_events(
            self,
            exclude_org_ids: List[int],
            preferred_roles: List[str],
            filter_params: FeedFilterParams
    ) -> List[Dict[str, Any]]:
        try:
            params: Dict[str, Any] = {"page_size": 20, "sort": "popularity"}
            if exclude_org_ids:
                params["exclude_org_ids"] = ",".join(map(str, exclude_org_ids))
            if preferred_roles:
                params["role_ids"] = ",".join(map(str, preferred_roles))

            url = f"{self.settings.EVENT_SERVICE_URL}/api/v1/events/popular"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        events = data.get("events", []) if isinstance(data, dict) else data

                        # ✅ Нормализуем org_id → organization_id
                        for ev in events:
                            if "organization_id" not in ev and "org_id" in ev:
                                ev["organization_id"] = ev["org_id"]
                        return events
                    elif response.status == 404:
                        logger.warning("Popular events endpoint not available (404)")
                        return []
                    logger.warning(f"Unexpected status {response.status} from {url}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching popular events: {e}")
            return []