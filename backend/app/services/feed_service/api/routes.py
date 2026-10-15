"""
API Routes для Feed Service.
✅ Внедрение зависимостей: repository, http_session, feed_generator.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import logging

from ..config import settings
from ..db.repository import FeedRepository, get_feed_repository
from ..core.http_client import get_async_session, AsyncSession
from ..core.feed_generator import FeedGenerator
from ..api.schemas import FeedResponse, FeedFilterParams

logger = logging.getLogger(__name__)

router = APIRouter()


def get_feed_generator(
    repository: FeedRepository = Depends(get_feed_repository),
    http_session: AsyncSession = Depends(get_async_session),
) -> FeedGenerator:
    """
    Factory-зависимость для создания FeedGenerator с инъекцией session.
    ✅ Session передаётся в сервис, а не создаётся заново на каждый запрос.
    """
    return FeedGenerator(
        repository=repository,
        settings=settings,
        http_session=http_session,  # <-- ключевое изменение
    )


@router.get("/feed", response_model=FeedResponse, summary="Get personalized feed")
async def get_user_feed(
    user_id: int = Query(..., ge=1, description="User ID"),
    filter_params: FeedFilterParams = Depends(),
    feed_generator: FeedGenerator = Depends(get_feed_generator),
):
    """
    Генерация персонализированной ленты мероприятий.

    - **user_id**: ID пользователя (обязательно)
    - **filter_params**: параметры фильтрации через query-params
    """
    try:
        feed = await feed_generator.generate_feed(
            user_id=user_id,
            filter_params=filter_params,
        )
        return feed
    except Exception as e:
        logger.error(f"Error generating feed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate feed: {str(e)}",
        )


@router.get("/feed/debug", summary="Debug feed generation")
async def debug_feed(
    user_id: int = Query(..., ge=1),
    feed_generator: FeedGenerator = Depends(get_feed_generator),
):
    """Debug-эндпоинт для проверки работы генератора."""
    from ..api.schemas import FeedFilterParams
    filter_params = FeedFilterParams()

    feed = await feed_generator.generate_feed(
        user_id=user_id,
        filter_params=filter_params,
    )
    return {
        "debug": True,
        "user_id": user_id,
        "sections_count": len(feed.sections),
        "total_events": feed.total_events,
    }