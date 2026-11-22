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


@router.get("/users/{user_id}/organizations", response_model=List[int])
async def list_user_organizations_internal(
    user_id: int,
    _: bool = Depends(verify_service_key),
    service: OrganizationService = Depends(get_service),
):
    return await service.list_user_organization_ids(user_id)
