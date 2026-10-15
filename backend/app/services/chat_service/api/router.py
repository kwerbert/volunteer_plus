"""API эндпоинты Chat Service"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import aiohttp
import logging
import asyncio
from app.services.chat_service.core.connection_manager import manager

from app.services.chat_service.api.deps import (
    get_db, get_current_user_id, verify_service_key, check_chat_access
)
from app.services.chat_service.api.schemas import (
    ChatCreateRequest, MessageCreateRequest, MarkReadRequest,
    ChatResponse, MessageResponse, MessagesListResponse, ChatListResponse,
    UserVerifyResponse, OrganizationVerifyResponse, EventVerifyResponse,
    NotificationRequest, ErrorResponse, ChatTypeEnum
)
from app.services.chat_service.db.repository import ChatRepository
from app.services.chat_service.core.service import ChatService
from app.services.chat_service.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Chat"])


# === Чаты ===

@router.post("/chats", response_model=ChatResponse, status_code=201)
async def create_chat(
        request: ChatCreateRequest,
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Создание нового чата"""
    service = ChatService(ChatRepository(db))

    # Валидация участников через внешние сервисы
    await _validate_participants(
        request.chat_type.value,
        request.participant_ids,
        request.organization_id,
        request.event_id
    )

    try:
        chat = await service.create_chat(
            chat_type=request.chat_type,
            creator_id=current_user_id,
            participant_ids=request.participant_ids,
            title=request.title,
            event_id=request.event_id,
            organization_id=request.organization_id
        )
        return chat
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chats", response_model=ChatListResponse)
async def get_user_chats(
        current_user_id: int = Depends(get_current_user_id),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
):
    """Получение списка чатов пользователя"""
    service = ChatService(ChatRepository(db))

    offset = (page - 1) * page_size
    chats, total = await service.get_user_chats(
        user_id=current_user_id,
        limit=page_size,
        offset=offset
    )

    return ChatListResponse(
        chats=chats,
        total=total,
        has_more=offset + len(chats) < total,
        next_offset=offset + page_size if offset + len(chats) < total else None
    )


@router.get("/chats/{chat_id}", response_model=ChatResponse)
async def get_chat(
        chat_id: int,
        _: bool = Depends(check_chat_access),
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Получение деталей чата"""
    service = ChatService(ChatRepository(db))
    chat = await service.get_chat_with_details(chat_id, current_user_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def leave_chat(
        chat_id: int,
        _: bool = Depends(check_chat_access),
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Покинуть чат (или удалить для personal чатов)"""
    service = ChatService(ChatRepository(db))
    await service.leave_chat(chat_id, current_user_id)
    return None


# === Сообщения ===

@router.get("/chats/{chat_id}/messages", response_model=MessagesListResponse)
async def get_chat_messages(
        chat_id: int,
        _: bool = Depends(check_chat_access),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        before_message_id: Optional[int] = Query(None, description="ID сообщения для пагинации назад"),
        db: AsyncSession = Depends(get_db)
):
    """Получение сообщений чата с пагинацией"""
    service = ChatService(ChatRepository(db))

    offset = (page - 1) * page_size
    messages, total = await service.get_messages(
        chat_id=chat_id,
        limit=page_size,
        offset=offset,
        before_message_id=before_message_id
    )

    return MessagesListResponse(
        messages=messages,
        total=total,
        has_more=offset + len(messages) < total,
        next_offset=offset + page_size if offset + len(messages) < total else None
    )


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
        chat_id: int,
        request: MessageCreateRequest,
        _: bool = Depends(check_chat_access),
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Отправка сообщения в чат"""
    service = ChatService(ChatRepository(db))

    message = await service.send_message(
        chat_id=chat_id,
        sender_id=current_user_id,
        content=request.content,
        message_type=request.message_type.value,
        attachment_url=request.attachment_url
    )

    # Отправка уведомления участникам (асинхронно, не блокируя ответ)
    await _send_notification_to_participants(
        chat_id=chat_id,
        sender_id=current_user_id,
        message_content=request.content,
        db=db
    )

    # следующие 2 строки должны идит после сохранения message
    message_response = MessageResponse.model_validate(message)
    await manager.broadcast(chat_id, message_response.model_dump(mode="json"))

    return message


@router.put("/messages/{message_id}/read", response_model=MessageResponse)
async def mark_message_read(
        message_id: int,
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Отметка сообщения как прочитанного"""
    service = ChatService(ChatRepository(db))

    message = await service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    # Проверка доступа к чату
    repo = ChatRepository(db)
    if not await repo.user_has_access_to_chat(message.chat_id, current_user_id):
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    return await service.mark_message_read(message_id)


@router.post("/chats/{chat_id}/read-all", response_model=dict)
async def mark_all_read(
        chat_id: int,
        _: bool = Depends(check_chat_access),
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Отметить все сообщения в чате как прочитанные"""
    service = ChatService(ChatRepository(db))
    count = await service.mark_chat_read(chat_id, current_user_id)
    return {"marked_read": count}


# === Service-to-Service endpoints ===

@router.get("/internal/chats/{chat_id}/members", response_model=List[int])
async def get_chat_members_internal(
        chat_id: int,
        _: bool = Depends(verify_service_key),
        db: AsyncSession = Depends(get_db)
):
    """Получение списка участников чата (для внутренних вызовов)"""
    repo = ChatRepository(db)
    members = await repo.get_chat_members(chat_id)
    return [m.user_id for m in members]


@router.post("/chats/organizer/{org_id}", response_model=ChatResponse, status_code=201)
async def create_organizer_chat(
        org_id: int,
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
):
    if not await _verify_organization(org_id):
        raise HTTPException(status_code=404, detail="Организация не найдена")

    service = ChatService(ChatRepository(db))
    try:
        # participant_ids пустой — организатор организации подтянется по org_id
        chat = await service.create_chat(
            chat_type=ChatTypeEnum.ORGANIZER,
            creator_id=current_user_id,
            participant_ids=[],
            organization_id=org_id,
        )
        return chat
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chats/event/{event_id}", response_model=ChatResponse, status_code=201)
async def create_event_chat(
        event_id: int,
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    # Проверка существования мероприятия
    if not await _verify_event(event_id):
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    """
    Создание группового чата для мероприятия
    Автоматически создаётся при регистрации первого волонтера
    """
    service = ChatService(ChatRepository(db))

    # Проверка что чат ещё не создан для этого мероприятия
    existing = await service.repo.find_event_chat(event_id)
    if existing:
        return existing

    try:
        # Получаем время окончания мероприятия (заглушка)
        from datetime import datetime, timezone, timedelta
        event_end_time = datetime.now(timezone.utc) + timedelta(hours=4)

        chat = await service.create_chat(
            chat_type=ChatTypeEnum.EVENT,
            creator_id=current_user_id,
            participant_ids=[current_user_id],
            event_id=event_id
        )

        # Планируем удаление (по умолчанию в 00:00 МСК)
        await service.schedule_event_chat_deletion(chat.id, event_end_time)

        return chat
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ✅ НОВЫЙ ЭНДПОИНТ: Удаление ORGANIZER чата
@router.delete("/chats/organizer/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organizer_chat(
        chat_id: int,
        current_user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """
    Удаление личного чата с организатором
    Может быть выполнено любой стороной
    """
    service = ChatService(ChatRepository(db))
    success = await service.delete_organizer_chat(chat_id, current_user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось удалить чат")
    return None


# ✅ ОБНОВЛЁННЫЙ ЭНДПОИНТ: Ручная очистка (для админа/крона)
@router.post("/internal/cleanup-expired-chats", response_model=dict)
async def cleanup_expired_chats(
        _: bool = Depends(verify_service_key),
        db: AsyncSession = Depends(get_db)
):
    """
    Очистка expired EVENT чатов
    Вызывается по крону раз в час
    ❌ Без уведомлений волонтёрам
    """
    service = ChatService(ChatRepository(db))
    count = await service.cleanup_expired_event_chats()
    return {"deleted_count": count}


# === Вспомогательные функции ===

async def _validate_participants(
        chat_type: str,
        participant_ids: List[int],
        organization_id: Optional[int],
        event_id: Optional[int]
):
    """Валидация участников и связанных сущностей через внешние сервисы"""

    # Проверка пользователей
    for user_id in participant_ids:
        if not await _verify_user(user_id):
            raise ValueError(f"Пользователь {user_id} не существует или неактивен")

    # Проверка организации для organization чатов
    if chat_type == "organization" and organization_id:
        if not await _verify_organization(organization_id):
            raise ValueError(f"Организация {organization_id} не существует")

    # Проверка мероприятия для event чатов
    if chat_type == "event" and event_id:
        if not await _verify_event(event_id):
            raise ValueError(f"Мероприятие {event_id} не существует")


async def _verify_user(user_id: int) -> bool:
    """Проверка существования пользователя через User Service"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"{settings.USER_SERVICE_URL}/api/v1/users/verify/{user_id}",
                    headers={"X-Service-Key": settings.SERVICE_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("exists") and data.get("is_active")
    except Exception as e:
        logger.error(f"Error verifying user {user_id}: {e}")
    return False


async def _verify_organization(org_id: int) -> bool:
    """Проверка организации через Organization Service"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"{settings.ORGANIZATION_SERVICE_URL}/api/v1/organizations/{org_id}",
                    timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Error verifying org {org_id}: {e}")
    return False


async def _verify_event(event_id: int) -> bool:
    """Проверка мероприятия через Event Service"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"{settings.EVENT_SERVICE_URL}/api/v1/events/{event_id}",
                    timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Error verifying event {event_id}: {e}")
    return False


async def _send_notification_to_participants(
        chat_id: int,
        sender_id: int,
        message_content: str,
        db: AsyncSession
):
    """Отправка пуш-уведомлений участникам чата"""
    try:
        repo = ChatRepository(db)
        members = await repo.get_chat_members(chat_id)

        # Предпросмотр сообщения
        preview = message_content[:100] + "..." if len(message_content) > 100 else message_content

        async with aiohttp.ClientSession() as session:
            for member in members:
                if member.user_id == sender_id or member.is_muted:
                    continue

                notification = NotificationRequest(
                    user_id=member.user_id,
                    title="Новое сообщение",
                    body=preview,
                    data={"chat_id": chat_id, "sender_id": sender_id},
                    priority="high"
                )

                # Асинхронная отправка (не ждём ответа)
                asyncio.create_task(
                    session.post(
                        f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications",
                        json=notification.model_dump(),
                        headers={"X-Service-Key": settings.SERVICE_API_KEY},
                        timeout=aiohttp.ClientTimeout(total=2)
                    )
                )
    except Exception as e:
        logger.error(f"Error sending notifications for chat {chat_id}: {e}")