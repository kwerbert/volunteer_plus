import aiohttp
import logging
from app.services.subscription_service.config import settings

logger = logging.getLogger(__name__)


async def check_entity_exists(url: str, entity_id: int, entity_name: str) -> bool:
    """
    Проверяет существование сущности (User или Organization) через HTTP запрос.
    """
    async with aiohttp.ClientSession() as session:
        try:
            target_url = f"{url}/api/v1/users/verify/{entity_id}"
            headers = {"X-Service-Key": settings.SERVICE_API_KEY}
            async with session.get(target_url, headers=headers, timeout=5) as response:
                if response.status == 200:
                    return True
                elif response.status == 404:
                    logger.warning(f"{entity_name} with ID {entity_id} not found at {url}")
                    return False
                else:
                    logger.error(f"Error checking {entity_name}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Connection error to {entity_name} service: {e}")
            # В продакшене лучше вернуть False или выбросить ошибку,
            # здесь для устойчивости считаем, что сервис недоступен = сущность не валидна
            return False


async def verify_organization(org_id: int) -> bool:
    return await check_entity_exists(settings.ORGANIZATION_SERVICE_URL, org_id, "Organization")


async def verify_user(user_id: int) -> bool:
    url = f"{settings.USER_SERVICE_URL}/api/v1/users/verify/{user_id}"
    headers = {"X-Service-Key": settings.SERVICE_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("exists", False) and data.get("is_active", False)
                return False
    except Exception:
        return False