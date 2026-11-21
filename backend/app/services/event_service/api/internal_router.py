"""Внутренние эндпоинты Event Service (X-Service-Key), этап 4.6."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service.api.deps import verify_service_key
from app.services.event_service.db.session import get_db_session
from app.services.event_service.schemas import OrganizationEventsCancelResponse
from app.services.event_service.service import EventService

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post(
    "/organizations/{org_id}/cancel-events",
    response_model=OrganizationEventsCancelResponse,
)
async def cancel_organization_events(
    org_id: int,
    _: bool = Depends(verify_service_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Вызывается organization_service при удалении организации:
    активные/будущие мероприятия → cancelled, завершённые остаются как есть."""
    return await EventService(db).cancel_organization_events(org_id)
