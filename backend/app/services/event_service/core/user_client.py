"""HTTP-клиент к user_service (X-Service-Key).

Нужен только для ортогональной привилегии is_admin (этап 4.2): роль в JWT
может устареть, а модератор определяется свежим флагом из user_service.
"""

import logging

import httpx
from fastapi import HTTPException, status

from app.services.event_service.config import settings

logger = logging.getLogger(__name__)


class UserServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.USER_SERVICE_URL
        self.api_key = settings.SERVICE_API_KEY

    async def is_admin(self, user_id: int) -> bool:
        url = f"{self.base_url}/api/v1/users/verify/{user_id}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    url, headers={"X-Service-Key": self.api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    return (
                        bool(data.get("exists"))
                        and bool(data.get("is_active"))
                        and bool(data.get("is_admin"))
                    )
                if response.status_code == 404:
                    return False
                logger.error(
                    "User Service verify/%s: HTTP %s", user_id, response.status_code
                )
        except httpx.HTTPError as e:
            logger.error("Connection error to User Service: %s", e)
        # Недоступность ≠ «не админ»: иначе получим ложный 403.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User Service недоступен",
        )
