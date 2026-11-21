from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service.api.deps import verify_service_key
from app.services.event_service.db.session import get_db_session
from app.services.event_service.schemas import (
    OrganizationEventsCancelResponse,
    ParticipationRoleInfoResponse,
)
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


@router.get(
    "/events/{event_id}/participations/{user_id}",
    response_model=ParticipationRoleInfoResponse,
)
async def get_participation_role_info(
    event_id: int,
    user_id: int,
    _: bool = Depends(verify_service_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Analytics_service получает event_role_id, название роли
    и hours_value. 404 — мероприятие/регистрация не найдены (→ дефолтные часы)."""
    info = await EventService(db).get_participation_role_info(event_id, user_id)
    if info is None:
        raise HTTPException(
            status_code=404, detail="Мероприятие или регистрация не найдены"
        )
    return info
