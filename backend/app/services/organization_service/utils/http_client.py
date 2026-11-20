"""HTTP-клиент к user_service (service-to-service, X-Service-Key)."""

import logging
from typing import Any, Dict, Optional
from urllib.parse import quote

import aiohttp
from fastapi import HTTPException, status

from app.services.organization_service.config import settings

logger = logging.getLogger(__name__)


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """GET /users/verify/{user_id} → {user_id, exists, is_active, role, is_admin}.

    None — пользователь не найден; 503 — user_service недоступен/ошибается
    (не подменяем недоступность сервиса «пользователь не существует»).
    """
    url = f"{settings.USER_SERVICE_URL}/api/v1/users/verify/{user_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"X-Service-Key": settings.SERVICE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 404:
                    return None
                logger.error(
                    "User Service verify/%s: HTTP %s", user_id, response.status
                )
    except aiohttp.ClientError as e:
        logger.error("Connection error to User Service: %s", e)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="User Service недоступен",
    )


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """GET /users/by-email/{email} → UserInternalResponse или None (404)."""
    url = f"{settings.USER_SERVICE_URL}/api/v1/users/by-email/{quote(email, safe='')}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"X-Service-Key": settings.SERVICE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 404:
                    return None
                logger.error(
                    "User Service by-email/%s: HTTP %s", email, response.status
                )
    except aiohttp.ClientError as e:
        logger.error("Connection error to User Service: %s", e)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="User Service недоступен",
    )
