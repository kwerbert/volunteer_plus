from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.services.subscription_service.db.session import get_db_session
from app.services.subscription_service.db.repository import SubscriptionRepository
from app.services.subscription_service.core.service import SubscriptionService
from app.services.subscription_service.api.schemas import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
    SubscriptionCheckResponse,
    MessageResponse
)

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.get("", response_model=List[SubscriptionResponse])
async def get_subscriptions(
        user_id: int = Query(..., description="ID пользователя"),
        active_only: bool = Query(True, description="Только активные"),
        db: AsyncSession = Depends(get_db_session)
):
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    return await service.get_user_subscriptions(user_id, active_only)


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
        sub_data: SubscriptionCreate,
        db: AsyncSession = Depends(get_db_session)
):
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)

    # Проверка уникальности и валидация внешних сущностей
    try:
        new_sub = await service.subscribe(sub_data.user_id, sub_data.org_id, sub_data.role)
        return new_sub
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{sub_id}", response_model=MessageResponse)
async def delete_subscription(
        sub_id: int,
        db: AsyncSession = Depends(get_db_session)
):
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)

    success = await service.unsubscribe(sub_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"message": "Successfully unsubscribed (soft deleted)"}


@router.put("/{sub_id}", response_model=SubscriptionResponse)
async def update_subscription(
        sub_id: int,
        sub_data: SubscriptionUpdate,
        db: AsyncSession = Depends(get_db_session)
):
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)

    updated_sub = await service.update_subscription(sub_id, sub_data)
    if not updated_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return updated_sub


@router.get("/check", response_model=SubscriptionCheckResponse)
async def check_subscription_status(
        user_id: int = Query(...),
        org_id: int = Query(...),
        db: AsyncSession = Depends(get_db_session)
):
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    return await service.check_status(user_id, org_id)