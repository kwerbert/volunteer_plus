import logging
from typing import Any, Dict, List, Optional

import aiohttp

from ..api.schemas import EventPreview, FeedFilterParams
from ..config import Settings
from .event_preview import build_event_preview

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
        user_location: Dict[str, Optional[float]],
    ) -> List[EventPreview]:
        recommendations: List[EventPreview] = []
        try:
            preferred_roles = await self._get_user_preferred_roles(user_id)
            popular_events = await self._fetch_popular_events(
                exclude_org_ids=exclude_org_ids,
                preferred_roles=preferred_roles,
                filter_params=filter_params,
            )
            for event in popular_events[:5]:
                # Нормализация org_id и дат — внутри общего билдера (этап 7.3)
                recommendations.append(build_event_preview(event))
            logger.info(
                f"Generated {len(recommendations)} recommendations for user {user_id}"
            )
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
        filter_params: FeedFilterParams,
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
                        events = (
                            data.get("events", []) if isinstance(data, dict) else data
                        )
                        # Нормализуем org_id → organization_id
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
