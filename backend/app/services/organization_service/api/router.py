from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.organization_service.api.deps import (
    get_current_user,
    require_admin,
    require_organizer,
)
from app.services.organization_service.db.session import get_db_session
from app.services.organization_service.schemas import (
    CurrentUser,
    OrganizationCreate,
    OrganizationOrganizerResponse,
    OrganizationResponse,
    OrganizationVerify,
    OrganizerAddRequest,
)
from app.services.organization_service.service import OrganizationService

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


def get_service(db: AsyncSession = Depends(get_db_session)) -> OrganizationService:
    return OrganizationService(db)


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    current_user: CurrentUser = Depends(require_organizer),
    service: OrganizationService = Depends(get_service),
):
    """Создание организации. Только ORGANIZER; один аккаунт — одна организация."""
    return await service.create(data, current_user)


# Публичные GET сохранены без авторизации: по ним без ключа ходят
# feed_service / chat_service / subscription_service.
@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    service: OrganizationService = Depends(get_service),
):
    return await service.get_list(category_id=category_id, verified=verified)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int, service: OrganizationService = Depends(get_service)
):
    org = await service.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/{org_id}/organizers", response_model=List[OrganizationOrganizerResponse])
async def list_organizers(
    org_id: int,
    _: CurrentUser = Depends(get_current_user),
    service: OrganizationService = Depends(get_service),
):
    """Список активных организаторов (владелец первым). Любой авторизованный."""
    return await service.list_organizers(org_id)


@router.post(
    "/{org_id}/organizers",
    response_model=OrganizationOrganizerResponse,
    status_code=201,
)
async def add_organizer(
    org_id: int,
    data: OrganizerAddRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrganizationService = Depends(get_service),
):
    """Добавить организатора по email. Только владелец.
    404 — email не найден; 422 — не ORGANIZER; 409 — уже в организации."""
    return await service.add_organizer(org_id, data.email, current_user)


@router.delete("/{org_id}/organizers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organizer(
    org_id: int,
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrganizationService = Depends(get_service),
):
    """Убрать организатора. Только владелец; владельца удалить нельзя."""
    await service.remove_organizer(org_id, user_id, current_user)
    return None


# === Удаление организации (мягкое) ===


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrganizationService = Depends(get_service),
):
    await service.delete_organization(org_id, current_user)
    return None


# === Верификация (заглушка) ===


@router.patch("/{org_id}/verify", response_model=OrganizationResponse)
async def verify_organization(
    org_id: int,
    data: OrganizationVerify,
    _: CurrentUser = Depends(require_admin),
    service: OrganizationService = Depends(get_service),
):
    return await service.verify_organization(org_id, data.verified)
