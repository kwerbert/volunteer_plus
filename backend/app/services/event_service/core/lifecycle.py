"""Фоновое обслуживание жизненного цикла мероприятий (этапы 4.3/4.4)."""

import asyncio
import logging

from app.services.event_service.config import settings
from app.services.event_service.db.session import async_session_maker

logger = logging.getLogger(__name__)


async def run_maintenance_once() -> dict:
    from app.services.event_service.service import EventService

    async with async_session_maker() as session:
        service = EventService(session)
        completed = await service.complete_expired_events()
        cleanup = await service.cleanup_cancelled_events()
    return {
        "completed_events": completed,
        "deleted_events": cleanup.deleted_events,
    }


async def maintenance_loop(interval_seconds: int | None = None) -> None:
    interval = interval_seconds or settings.MAINTENANCE_INTERVAL_SECONDS
    while True:
        try:
            stats = await run_maintenance_once()
            if stats["completed_events"] or stats["deleted_events"]:
                logger.info("Event maintenance: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Event maintenance failed")
        await asyncio.sleep(interval)
