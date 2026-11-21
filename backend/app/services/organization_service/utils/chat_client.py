"""HTTP-клиент к chat_service.

Синхронизация состава чатов — побочный эффект управления организаторами:
недоступность chat_service не должна ронять добавление/удаление организатора.
Состав EVENT-чатов самовосстанавливается: ensure_event_chat добавляет всех
организаторов при каждой новой регистрации.
"""

import asyncio
import logging

import aiohttp

from app.services.organization_service.config import settings

logger = logging.getLogger(__name__)


async def _sync_organizer(action: str, org_id: int, user_id: int) -> bool:
    url = f"{settings.CHAT_SERVICE_URL}/internal/organizations/{org_id}/{action}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"user_id": user_id},
                headers={"X-Service-Key": settings.SERVICE_API_KEY},
                timeout=aiohttp.ClientTimeout(total=settings.CHAT_TIMEOUT_SECONDS),
            ) as response:
                if response.status == 200:
                    return True
                logger.error(
                    "Chat Service %s org=%s user=%s: HTTP %s",
                    action,
                    org_id,
                    user_id,
                    response.status,
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(
            "Connection error to Chat Service (%s org=%s): %s", action, org_id, e
        )
    return False


async def add_organizer_to_chats(org_id: int, user_id: int) -> bool:
    """6.2: добавить организатора во все EVENT-чаты организации."""
    return await _sync_organizer("add-organizer", org_id, user_id)


async def remove_organizer_from_chats(org_id: int, user_id: int) -> bool:
    """6.3: убрать организатора из всех EVENT-чатов организации."""
    return await _sync_organizer("remove-organizer", org_id, user_id)
