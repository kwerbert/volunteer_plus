"""Внутренние эндпоинты Chat Service (X-Service-Key).

Контракт авторизации как в user/org/event: нет ключа → 401, неверный → 403.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_service.api.deps import verify_service_key
from app.services.chat_service.core.chat_lifecycle import (
    add_organizer_to_org_chats,
    ensure_event_chat,
    remove_organizer_from_org_chats,
)
from app.services.chat_service.db.session import get_db_session

router = APIRouter(prefix="/internal", tags=["Internal"])


class EnsureChatRequest(BaseModel):
    user_id: int
    organization_id: int


class EnsureChatResponse(BaseModel):
    chat_id: int


class OrganizerSyncRequest(BaseModel):
    user_id: int


class OrganizerSyncResponse(BaseModel):
    organization_id: int
    user_id: int
    chats_updated: int


@router.post("/events/{event_id}/ensure-chat", response_model=EnsureChatResponse)
async def ensure_event_chat_endpoint(
    event_id: int,
    request: EnsureChatRequest,
    _: bool = Depends(verify_service_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Вызывается event_service при регистрации: чат + волонтёр + организаторы (6.1)."""
    chat_id = await ensure_event_chat(
        db=db,
        event_id=event_id,
        user_id=request.user_id,
        organization_id=request.organization_id,
    )
    return EnsureChatResponse(chat_id=chat_id)


@router.post(
    "/organizations/{org_id}/add-organizer", response_model=OrganizerSyncResponse
)
async def add_organizer_endpoint(
    org_id: int,
    request: OrganizerSyncRequest,
    _: bool = Depends(verify_service_key),
    db: AsyncSession = Depends(get_db_session),
):
    """6.2: organization_service добавила организатора — синхронизируем чаты."""
    updated = await add_organizer_to_org_chats(db, org_id, request.user_id)
    return OrganizerSyncResponse(
        organization_id=org_id, user_id=request.user_id, chats_updated=updated
    )


@router.post(
    "/organizations/{org_id}/remove-organizer", response_model=OrganizerSyncResponse
)
async def remove_organizer_endpoint(
    org_id: int,
    request: OrganizerSyncRequest,
    _: bool = Depends(verify_service_key),
    db: AsyncSession = Depends(get_db_session),
):
    """6.3: organization_service убрала организатора — убираем из чатов."""
    updated = await remove_organizer_from_org_chats(db, org_id, request.user_id)
    return OrganizerSyncResponse(
        organization_id=org_id, user_id=request.user_id, chats_updated=updated
    )
