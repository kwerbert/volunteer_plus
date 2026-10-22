import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List

from app.services.event_service.db.session import get_db_session
from app.services.event_service.service import EventService
from app.services.event_service.schemas import (
    EventCreate, EventResponse, RegisterRequest,
    ParticipationResponse, CheckInRequest
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/events", tags=["Events"])

@router.get("", response_model=List[EventResponse])
async def get_events(
    org_ids: Optional[str] = Query(None, description="Comma-separated org IDs"),
    date_from: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    ids_list = [int(x) for x in org_ids.split(",")] if org_ids else None
    try:
        events = await service.get_events(org_ids=ids_list, date_from=date_from)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    try:
        new_event = await service.create_event(event_data)
        return new_event
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{event_id}/register", response_model=ParticipationResponse)
async def register_for_event(
    event_id: int,
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    try:
        participation = await service.register_user(event_id, request)
        return participation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{event_id}/check-in", response_model=ParticipationResponse)
async def check_in_event(
    event_id: int,
    request: CheckInRequest,
    db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    try:
        participation = await service.check_in(event_id, request.user_id, request.qr_code)
        return participation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/popular", response_model=dict)
async def get_popular_events(
    page_size: int = Query(20, ge=1, le=100),
    exclude_org_ids: Optional[str] = Query(None, description="Comma-separated org IDs"),
    role_ids: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Популярные события с фильтрами.
    - exclude_org_ids: CSV целых ID, события этих организаций исключаются.
    - sort=popularity: сортировка по числу регистраций.
    - role_ids: НЕ поддерживается (в Event нет поля роли; роли хранятся
      только в Participation.role_id, к тому же числом). Параметр принимаем,
      чтобы клиент не получал 422, но применяем только после явной доработки схемы.
    """
    service = EventService(db)

    excluded: List[int] = []
    if exclude_org_ids:
        try:
            excluded = [int(x) for x in exclude_org_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="exclude_org_ids must be comma-separated integers"
            )

    if role_ids:
        # TOD0: реализовать фильтр по ролям, когда в Event появится required_role_id :)
        # (или через JOIN с Participation.role_id, если клиент будет присылать ID).
        logger.warning(
            "popular: role_ids filter is not supported yet (got %r), ignoring",
            role_ids,
        )

    events = await service.get_popular_events(
        exclude_org_ids=excluded or None,
        limit=page_size,
        sort=sort,
    )

    return {"events": [EventResponse.model_validate(e).model_dump() for e in events]}

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    event = await service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event