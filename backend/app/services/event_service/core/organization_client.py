"""HTTP-клиент к organization_service (service-to-service, X-Service-Key).

Единый источник правды о правах на организацию — organization_organizers.
"""

import logging
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException, status

from app.services.event_service.config import settings

logger = logging.getLogger(__name__)


class OrganizationServiceClient:
    def __init__(self):
        self.base_url = settings.ORGANIZATION_SERVICE_URL
        self.api_key = settings.SERVICE_API_KEY

    async def get_organizers(self, org_id: int) -> List[Dict[str, Any]]:
        """Список активных организаторов. 404 — организации нет/неактивна;
        503 — сервис недоступен (не подменяем недоступность «нет прав»)."""
        url = f"{self.base_url}/internal/organizations/{org_id}/organizers"
        headers = {"X-Service-Key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Организация не найдена",
                    )
                logger.error(
                    "Organization Service organizers/%s: HTTP %s",
                    org_id,
                    response.status_code,
                )
        except httpx.HTTPError as e:
            logger.error("Connection error to Organization Service: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Organization Service недоступен",
        )

    async def is_organizer(self, org_id: int, user_id: int) -> bool:
        organizers = await self.get_organizers(org_id)
        return any(int(o["user_id"]) == user_id for o in organizers)
