"""Внутренние эндпоинты Organization Service (X-Service-Key).

Этап 3: event_service проверяет членство пользователя в organization_organizers,
не пробрасывая пользовательский JWT и не ходя лишний раз в user_service.
Единый источник правды — organization_organizers (см. ТЗ «НЕ ЗАБЫТЬ»).
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.organization_service.api.deps import verify_service_key
from app.services.organization_service.db.session import get_db_session
from app.services.organization_service.schemas import OrganizationOrganizerResponse
from app.services.organization_service.service import OrganizationService

router = APIRouter(prefix="/internal", tags=["Internal"])


def get_service(db: AsyncSession = Depends(get_db_session)) -> OrganizationService:
    return OrganizationService(db)


@router.get(
    "/organizations/{org_id}/organizers",
    response_model=List[OrganizationOrganizerResponse],
)
async def list_organizers_internal(
    org_id: int,
    _: bool = Depends(verify_service_key),
    service: OrganizationService = Depends(get_service),
):
    """Активные организаторы организации для других сервисов. 404 — орг не найдена."""
    return await service.list_organizers(org_id)
