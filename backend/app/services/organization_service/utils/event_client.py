"""HTTP-клиент к event_service (X-Service-Key)"""

import logging
from typing import Any, Dict

import aiohttp
from fastapi import HTTPException, status

from app.services.organization_service.config import settings

logger = logging.getLogger(__name__)


async def cancel_organization_events(org_id: int) -> Dict[str, Any]:
    """Отменяет активные мероприятия организации перед её удалением.
    Недоступность event_service → 503: организацию не «полуудаляем»."""
    url = f"{settings.EVENT_SERVICE_URL}/internal/organizations/{org_id}/cancel-events"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"X-Service-Key": settings.SERVICE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(
                    "Event Service cancel-events/%s: HTTP %s", org_id, response.status
                )
    except aiohttp.ClientError as e:
        logger.error("Connection error to Event Service: %s", e)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Event Service недоступен: не удалось отменить мероприятия организации",
    )
