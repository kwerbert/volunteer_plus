from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import FeedServiceLog
from fastapi import Depends
from .session import get_db_session

class FeedRepository:
    def __init__(self, session: AsyncSession, settings):
        self.session = session
        self.settings = settings

    async def log_feed_generation(
        self,
        user_id: int,
        request_id: str,
        processing_time_ms: int,
        event_count: int,
        cache_hit: bool,
        error_message: Optional[str] = None
    ):
        log = FeedServiceLog(
            user_id=user_id,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
            event_count=event_count,
            cache_hit=cache_hit,
            error_message=error_message
        )
        self.session.add(log)
        await self.session.commit()

    async def get_recent_feed_stats(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(FeedServiceLog).where(FeedServiceLog.created_at >= cutoff_time)
        result = await self.session.execute(stmt)
        logs = list(result.scalars().all())

        if not logs:
            return {
                "total_requests": 0, "avg_processing_time_ms": 0,
                "cache_hit_rate_percent": 0, "error_rate_percent": 0
            }

        total_requests = len(logs)
        avg_time = sum(log.processing_time_ms for log in logs) / total_requests
        cache_hits = sum(1 for log in logs if log.cache_hit)
        errors = sum(1 for log in logs if log.error_message)

        return {
            "total_requests": total_requests,
            "avg_processing_time_ms": round(avg_time, 2),
            "cache_hit_rate_percent": round((cache_hits / total_requests) * 100, 2),
            "error_rate_percent": round((errors / total_requests) * 100, 2)
        }

async def get_feed_repository(
        db_session: AsyncSession = Depends(get_db_session),
        settings=Depends(lambda: __import__('app.services.feed_service.config', fromlist=['settings']).settings)
) -> FeedRepository:
    return FeedRepository(session=db_session, settings=settings)