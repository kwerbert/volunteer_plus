# app/services/analytics_service/api/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.services.analytics_service.db.session import get_db_session
from app.services.analytics_service.db.repository import AnalyticsRepository
from app.services.analytics_service.core.service import AnalyticsService
from app.services.analytics_service.api.schemas import (
    UserStatsResponse,
    OrganizationStatsResponse,
    MonthlyStatsResponse,
    EventCompleteRequest,
    EventCompleteResponse,
    PreferredRolesResponse
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/users/{user_id}", response_model=UserStatsResponse)
async def get_user_analytics(
        user_id: int,
        db: AsyncSession = Depends(get_db_session)
):
    """Получение общей статистики волонтёра"""
    repo = AnalyticsRepository(db)
    service = AnalyticsService(repo)

    try:
        return await service.get_user_analytics(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/by-organization", response_model=OrganizationStatsResponse)
async def get_organization_analytics(
        user_id: int,
        db: AsyncSession = Depends(get_db_session)
):
    """Статистика по организациям"""
    repo = AnalyticsRepository(db)
    service = AnalyticsService(repo)

    try:
        return await service.get_organization_analytics(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/monthly", response_model=MonthlyStatsResponse)
async def get_monthly_analytics(
        user_id: int,
        months: int = Query(12, ge=1, le=24, description="Количество месяцев"),
        db: AsyncSession = Depends(get_db_session)
):
    """Ежемесячная статистика волонтёрства"""
    repo = AnalyticsRepository(db)
    service = AnalyticsService(repo)

    try:
        return await service.get_monthly_analytics(user_id, months)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/complete", response_model=EventCompleteResponse)
async def complete_event(
        event_id: int,
        request: EventCompleteRequest,
        db: AsyncSession = Depends(get_db_session)
):
    """Завершение мероприятия и учёт часов"""
    repo = AnalyticsRepository(db)
    service = AnalyticsService(repo)

    try:
        return await service.complete_event(
            event_id=event_id,
            user_id=request.user_id,
            hours=request.hours_worked,
            role=request.role
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/preferred-roles", response_model=PreferredRolesResponse)
async def get_preferred_roles(
        user_id: int,
        db: AsyncSession = Depends(get_db_session)
):
    """Предпочтительные роли пользователя (для Feed Service)"""
    repo = AnalyticsRepository(db)
    service = AnalyticsService(repo)

    try:
        return await service.get_preferred_roles(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))