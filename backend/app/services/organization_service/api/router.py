from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

# ❌ БЫЛО:
# from app.database import get_db

# ✅ СТАЛО: используем локальную сессию сервиса
from app.services.organization_service.db.session import get_db_session

from app.services.organization_service.service import OrganizationService
from app.services.organization_service.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationVerify
)

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])

@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session)  # ← теперь соответствует тому, что в тестах
):
    service = OrganizationService(db)
    try:
        org = await service.create(data)
        return org
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    db: AsyncSession = Depends(get_db_session)  # ← везде заменили
):
    service = OrganizationService(db)
    orgs = await service.get_list(category_id=category_id, verified=verified)
    return orgs

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: int, db: AsyncSession = Depends(get_db_session)):
    service = OrganizationService(db)
    org = await service.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.post("/{org_id}/verify", response_model=OrganizationResponse)
async def verify_organization(
    org_id: int,
    data: OrganizationVerify,
    db: AsyncSession = Depends(get_db_session)
):
    service = OrganizationService(db)
    try:
        org = await service.verify_organization(org_id, data.verified)
        return org
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))