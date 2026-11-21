"""HTTP-клиент к notification_service

Отправка не должна ронять бизнес-операцию: уведомление уже сохранено в БД
notification_service, даже если у пользователя нет push-токенов (NO_TOKENS).
Поэтому — fire-and-forget фоновая задача со своей httpx-сессией.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.services.event_service.config import settings
from app.utils.notifications_enums import NotificationType, Priority

logger = logging.getLogger(__name__)

# Ссылки на фоновые задачи, чтобы их не собрал GC
_background_tasks: set[asyncio.Task] = set()

_SEND_ATTEMPTS = 2
_RETRY_BACKOFF_SECONDS = 0.5
_MAX_PARALLEL = 10


class NotificationServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.NOTIFICATION_SERVICE_URL
        self.api_key = settings.SERVICE_API_KEY
        self.timeout = settings.NOTIFICATION_TIMEOUT_SECONDS

    async def _send_one(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        user_id: int,
        title: str,
        body: str,
        notification_type: NotificationType,
        priority: Priority,
        data: Optional[Dict[str, Any]],
    ) -> bool:
        payload = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "notification_type": notification_type.value,
            "priority": priority.value,
            "data": data or {},
        }
        async with semaphore:
            for attempt in range(1, _SEND_ATTEMPTS + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/api/v1/notifications",
                        json=payload,
                        headers={"X-Service-Key": self.api_key},
                    )
                except httpx.HTTPError as e:
                    logger.warning(
                        "Notification to user %s failed (attempt %s): %s",
                        user_id,
                        attempt,
                        e,
                    )
                else:
                    if response.status_code < 400:
                        # 2xx: сюда попадает и NO_TOKENS — уведомление сохранено.
                        return True
                    if response.status_code < 500 and response.status_code != 429:
                        logger.warning(
                            "Notification to user %s rejected: HTTP %s %s",
                            user_id,
                            response.status_code,
                            response.text[:200],
                        )
                        return False  # 4xx не ретраим — это баг/auth
                    logger.warning(
                        "Notification to user %s: HTTP %s (attempt %s)",
                        user_id,
                        response.status_code,
                        attempt,
                    )
                if attempt < _SEND_ATTEMPTS:
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS * attempt)
            return False

    async def send_bulk(
        self,
        user_ids: List[int],
        title: str,
        body: str,
        notification_type: NotificationType,
        priority: Priority = Priority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        recipients = sorted({int(u) for u in user_ids})
        if not recipients:
            return 0
        semaphore = asyncio.Semaphore(_MAX_PARALLEL)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                results = await asyncio.gather(
                    *[
                        self._send_one(
                            client,
                            semaphore,
                            u,
                            title,
                            body,
                            notification_type,
                            priority,
                            data,
                        )
                        for u in recipients
                    ],
                    return_exceptions=True,
                )
        except Exception:
            logger.exception("Bulk notification failed (%s)", notification_type.value)
            return 0
        sent = sum(1 for r in results if r is True)
        logger.info(
            "Notification %s: %s/%s delivered",
            notification_type.value,
            sent,
            len(recipients),
        )
        return sent

    def notify_background(
        self,
        user_ids: List[int],
        title: str,
        body: str,
        notification_type: NotificationType,
        priority: Priority = Priority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        recipients = sorted({int(u) for u in user_ids})
        if not recipients:
            return
        task = asyncio.create_task(
            self.send_bulk(recipients, title, body, notification_type, priority, data)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
