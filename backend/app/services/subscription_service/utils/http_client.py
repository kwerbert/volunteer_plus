import aiohttp
import logging
from app.services.subscription_service.config import settings

logger = logging.getLogger(__name__)


async def verify_user(user_id: int) -> bool:
    """
    Проверяет существование и активность пользователя через User Service.
    Использует внутренний эндпоинт /users/verify/{user_id}.
    """
    url = f"{settings.USER_SERVICE_URL}/api/v1/users/verify/{user_id}"
    headers = {"X-Service-Key": settings.SERVICE_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return bool(data.get("exists", False)) and bool(data.get("is_active", False))
                if response.status == 404:
                    logger.warning(f"User with ID {user_id} not found")
                    return False
                logger.error(f"Error checking User {user_id}: HTTP {response.status}")
                return False
    except Exception as e:
        logger.error(f"Connection error to User service: {e}")
        return False


async def verify_organization(org_id: int) -> bool:
    """
    Проверяет существование организации через Organization Service.
    Использует публичный эндпоинт GET /organizations/{org_id} (200/404).
    """
    url = f"{settings.ORGANIZATION_SERVICE_URL}/api/v1/organizations/{org_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return True
                if response.status == 404:
                    logger.warning(f"Organization with ID {org_id} not found")
                    return False
                logger.error(f"Error checking Organization {org_id}: HTTP {response.status}")
                return False
    except Exception as e:
        logger.error(f"Connection error to Organization service: {e}")
        return False