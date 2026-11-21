"""HTTP-клиент к organization_service (этап 5.3).

Единый источник правды об организаторах — organization_organizers.
Уведомление — побочный эффект: недоступность сервиса не роняет отправку
сообщения, поэтому ошибки гасятся в [] (в отличие от event_service,
где 503 обязан отличать «нет прав» от «сервис лёг»).
"""

import logging
from typing import List

import aiohttp

from app.services.chat_service.config import settings

logger = logging.getLogger(__name__)


class OrganizationServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.ORGANIZATION_SERVICE_URL
        self.api_key = settings.SERVICE_API_KEY

    async def get_organizer_ids(self, organization_id: int) -> List[int]:
        url = f"{self.base_url}/internal/organizations/{organization_id}/organizers"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"X-Service-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return sorted({int(o["user_id"]) for o in data})
                    logger.warning(
                        "Organization Service organizers/%s: HTTP %s",
                        organization_id,
                        response.status,
                    )
        except Exception as e:
            logger.warning("Cannot fetch organizers of org %s: %r", organization_id, e)
        return []


organization_client = OrganizationServiceClient()
