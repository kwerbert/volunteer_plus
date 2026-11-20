import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service.api.deps import get_current_user_id
from app.services.event_service.db.session import get_db_session
from app.services.event_service.schemas import (
    CheckInRequest,
    EventCreate,
    EventResponse,
    EventUpdate,
    ParticipationResponse,
    RegisterRequest,
)
from app.services.event_service.service import EventService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.get("", response_model=List[EventResponse])
async def get_events(
    org_ids: Optional[str] = Query(None, description="Comma-separated org IDs"),
    date_from: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    service = EventService(db)
    ids_list = [int(x) for x in org_ids.split(",")] if org_ids else None
    return await service.get_events(org_ids=ids_list, date_from=date_from)


@router.post("", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Создание мероприятия. Только организатор организации (этап 3.1)."""
    service = EventService(db)
    try:
        return await service.create_event(event_data, current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/popular", response_model=dict)
async def get_popular_events(
    page_size: int = Query(20, ge=1, le=100),
    exclude_org_ids: Optional[str] = Query(None),
    role_ids: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    service = EventService(db)
    excluded: List[int] = []
    if exclude_org_ids:
        try:
            excluded = [int(x) for x in exclude_org_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="exclude_org_ids must be comma-separated integers",
            )
    if role_ids:
        logger.warning("popular: role_ids filter not supported yet, ignoring")
    events = await service.get_popular_events(
        exclude_org_ids=excluded or None, limit=page_size, sort=sort
    )
    return {"events": [e.model_dump() for e in events]}


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db_session)):
    """Детальная карточка: роли с часами, лимитами и registered_count (этап 3.7)."""
    service = EventService(db)
    event = await service.get_event_detail(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    data: EventUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Редактирование. Только организатор организации (этап 3.1)."""
    service = EventService(db)
    try:
        return await service.update_event(event_id, data, current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{event_id}/register", response_model=ParticipationResponse)
async def register_for_event(
    event_id: int, request: RegisterRequest, db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    try:
        return await service.register_user(event_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e


@router.post("/{event_id}/check-in", response_model=ParticipationResponse)
async def check_in_event(
    event_id: int, request: CheckInRequest, db: AsyncSession = Depends(get_db_session)
):
    service = EventService(db)
    try:
        return await service.check_in(event_id, request.user_id, request.qr_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
