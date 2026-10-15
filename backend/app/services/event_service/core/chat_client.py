import httpx
import logging
from typing import Optional
from app.services.event_service.config import settings

logger = logging.getLogger(__name__)

class ChatServiceClient:
    def __init__(self):
        self.base_url = settings.CHAT_SERVICE_URL
        self.api_key = settings.SERVICE_API_KEY

    async def ensure_event_chat(
        self,
        event_id: int,
        user_id: int,
        organization_id: int
    ) -> Optional[int]:
        """Вызывает внутренний эндпоинт чат-сервиса для создания/добавления в чат"""
        url = f"{self.base_url}/internal/events/{event_id}/ensure-chat"
        payload = {
            "user_id": user_id,
            "organization_id": organization_id
        }
        headers = {
            "X-Service-Key": self.api_key,
            "Content-Type": "application/json"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("chat_id")
                else:
                    logger.error(
                        f"Failed to ensure chat for event {event_id}, "
                        f"status={response.status_code}, body={response.text}"
                    )
                    return None
        except Exception as e:
            logger.exception(f"Error calling chat service for event {event_id}: {e}")
            return None