"""HTTP-клиент к analytics_service.
Учёт часов при завершении мероприятия — побочный эффект: недоступность
analytics не роняет завершение (fire-and-forget, паттерн notification_client).
БЕЗ ретраев: у analytics нет идемпотентности по (event, user) — повтор после
таймаута может задвоить часы. Лучше потерять начисление и залогировать,
чем задвоить. Гард от повторного триггера — сам переход статуса
active→completed (completed повторно не завершается).
"""

import asyncio
import logging
from typing import List

import httpx

from app.services.event_service.config import settings

logger = logging.getLogger(__name__)

# Ссылки на фоновые задачи, чтобы их не собрал GC
_background_tasks: set[asyncio.Task] = set()
_MAX_PARALLEL = 10


class AnalyticsServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.ANALYTICS_SERVICE_URL
        self.api_key = settings.SERVICE_API_KEY

    async def _complete_one(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        event_id: int,
        user_id: int,
    ) -> bool:
        url = f"{self.base_url}/api/v1/analytics/events/{event_id}/complete"
        async with semaphore:
            try:
                # hours/role не передаём: analytics сам возьмёт hours_value
                # и name роли из регистрации (этап 8.1/8.2).
                response = await client.post(
                    url,
                    json={"user_id": user_id},
                    headers={"X-Service-Key": self.api_key},
                )
            except httpx.HTTPError as e:
                logger.warning(
                    "Analytics complete event=%s user=%s failed: %s",
                    event_id,
                    user_id,
                    e,
                )
                return False

        if response.status_code >= 400:
            logger.warning(
                "Analytics complete event=%s user=%s: HTTP %s",
                event_id,
                user_id,
                response.status_code,
            )
            return False
        try:
            data = response.json()
        except ValueError:
            data = {}
        if isinstance(data, dict) and data.get("success") is False:
            logger.warning(
                "Analytics complete event=%s user=%s rejected: %s",
                event_id,
                user_id,
                data.get("message"),
            )
            return False
        return True

    async def complete_for_users(self, event_id: int, user_ids: List[int]) -> int:
        recipients = sorted({int(u) for u in user_ids})
        if not recipients:
            return 0
        semaphore = asyncio.Semaphore(_MAX_PARALLEL)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                results = await asyncio.gather(
                    *[
                        self._complete_one(client, semaphore, event_id, u)
                        for u in recipients
                    ],
                    return_exceptions=True,
                )
        except Exception:
            logger.exception("Analytics bulk complete failed for event %s", event_id)
            return 0
        credited = sum(1 for r in results if r is True)
        logger.info(
            "Analytics: event %s completed, hours credited %s/%s",
            event_id,
            credited,
            len(recipients),
        )
        return credited

    def complete_background(self, event_id: int, user_ids: List[int]) -> None:
        recipients = sorted({int(u) for u in user_ids})
        if not recipients:
            return
        task = asyncio.create_task(self.complete_for_users(event_id, recipients))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
