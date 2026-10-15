"""Бизнес-логика Chat Service"""
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
import logging
from app.services.chat_service.db.repository import ChatRepository
from app.services.chat_service.api.schemas import (
    ChatResponse, MessageResponse, ChatMemberResponse, ChatTypeEnum
)
from app.services.chat_service.db.models import Chat, Message, ChatMember

logger = logging.getLogger(__name__)

class ChatService:
    """Основной сервис для операций с чатами"""
    def __init__(self, repo: ChatRepository):
        self.repo = repo

    # === Chat Operations ===
    async def schedule_event_chat_deletion(
        self,
        chat_id: int,
        event_end_time: datetime,
        custom_deletion_config: Optional[dict] = None
    ) -> bool:
        """Планирует удаление чата мероприятия"""
        from datetime import timedelta, timezone
        msk_tz = timezone(timedelta(hours=3))
        event_end_msk = event_end_time.astimezone(msk_tz)

        if custom_deletion_config:
            delay_hours = custom_deletion_config.get("deletion_delay_hours", 24)
            scheduled_time = event_end_msk + timedelta(hours=delay_hours)
        else:
            tomorrow_midnight = datetime(
                event_end_msk.year, event_end_msk.month, event_end_msk.day,
                0, 0, 0, tzinfo=msk_tz
            ) + timedelta(days=1)
            scheduled_time = tomorrow_midnight

        chat = await self.repo.get_chat_by_id(chat_id)
        if not chat:
            return False

        await self.repo.update_chat(
            chat_id,
            scheduled_delete_at=scheduled_time,
            deletion_config=custom_deletion_config
        )
        return True

    async def cleanup_expired_event_chats(self) -> int:
        """Удаляет EVENT чаты у которых наступило scheduled_delete_at"""
        now = datetime.now(timezone.utc)
        expired_chats = await self.repo.get_chats_for_deletion(now)
        deleted_count = 0
        for chat in expired_chats:
            await self.repo.deactivate_chat(chat.id)
            deleted_count += 1
        return deleted_count

    async def delete_organizer_chat(
        self,
        chat_id: int,
        user_id: int
    ) -> bool:
        """Удаление личного чата с организатором (любой стороной)"""
        chat = await self.repo.get_chat_by_id(chat_id)
        if not chat or chat.chat_type != ChatTypeEnum.ORGANIZER:
            return False
        if not await self.repo.user_has_access_to_chat(chat_id, user_id):
            return False
        return await self.repo.deactivate_chat(chat_id)

    async def create_chat(
            self,
            chat_type: ChatTypeEnum,
            creator_id: int,
            participant_ids: List[int],
            title: Optional[str] = None,
            event_id: Optional[int] = None,
            organization_id: Optional[int] = None
    ) -> ChatResponse:
        # ORGANIZER-чат ищем по (creator_id, organization_id)
        if chat_type == ChatTypeEnum.ORGANIZER and organization_id is not None:
            existing = await self.repo.find_organizer_chat(creator_id, organization_id)
            if existing:
                return await self._build_chat_response(existing, creator_id)

        chat = await self.repo.create_chat(
            chat_type=chat_type,
            title=title,
            event_id=event_id,
            organization_id=organization_id
        )
        await self.repo.add_member(chat.id, creator_id, role="admin")
        for user_id in participant_ids:
            if user_id != creator_id:
                await self.repo.add_member(chat.id, user_id, role="member")

        return await self._build_chat_response(chat, creator_id)

    async def get_user_chats(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[ChatResponse], int]:
        """Получение списка чатов пользователя"""
        chats = await self.repo.get_user_chats(user_id, limit=limit, offset=offset)
        all_chats = await self.repo.get_user_chats(user_id, limit=1000, offset=0)
        total = len(all_chats)
        responses = []
        for chat in chats:
            response = await self._build_chat_response(chat, user_id)
            responses.append(response)
        return responses, total

    async def get_chat_with_details(
        self,
        chat_id: int,
        current_user_id: int
    ) -> Optional[ChatResponse]:
        """Получение чата с деталями и unread count"""
        chat = await self.repo.get_chat_by_id(chat_id)
        if not chat:
            return None
        return await self._build_chat_response(chat, current_user_id)

    async def leave_chat(self, chat_id: int, user_id: int) -> bool:
        """Покинуть чат"""
        chat = await self.repo.get_chat_by_id(chat_id)
        if not chat:
            return False

        # ИСПРАВЛЕНО: ORGANIZER вместо PERSONAL
        if chat.chat_type == ChatTypeEnum.ORGANIZER:
            members = await self.repo.get_chat_members(chat_id)
            if len(members) <= 2:
                return await self.repo.deactivate_chat(chat_id)
        return await self.repo.remove_member(chat_id, user_id)

    # === Message Operations ===
    async def send_message(
            self,
            chat_id: int,
            sender_id: int,
            content: str,
            message_type: str = "text",
            attachment_url: Optional[str] = None
    ) -> MessageResponse:
        if not await self.repo.user_has_access_to_chat(chat_id, sender_id):
            raise ValueError("Нет доступа к чату")

        message = await self.repo.create_message(
            chat_id=chat_id, sender_id=sender_id, content=content,
            message_type=message_type, attachment_url=attachment_url
        )
        # updated_at обновится сам через onupdate
        await self.repo.update_chat(chat_id)
        return self._message_to_response(message)

    async def get_messages(
        self,
        chat_id: int,
        limit: int = 20,
        offset: int = 0,
        before_message_id: Optional[int] = None
    ) -> Tuple[List[MessageResponse], int]:
        messages = await self.repo.get_messages(
            chat_id=chat_id, limit=limit, offset=offset, before_message_id=before_message_id
        )
        all_msgs = await self.repo.get_messages(chat_id, limit=10000)
        total = len(all_msgs)
        responses = [self._message_to_response(m) for m in messages]
        return responses, total

    async def get_message(self, message_id: int) -> Optional[Message]:
        return await self.repo.get_message_by_id(message_id)

    async def mark_message_read(self, message_id: int) -> Optional[MessageResponse]:
        message = await self.repo.mark_message_read(message_id)
        return self._message_to_response(message) if message else None

    async def mark_chat_read(self, chat_id: int, user_id: int) -> int:
        return await self.repo.mark_chat_messages_read(chat_id, user_id)

    # === Helpers ===
    async def _build_chat_response(
        self,
        chat: Chat,
        current_user_id: int
    ) -> ChatResponse:
        last_messages = await self.repo.get_messages(chat.id, limit=1)
        last_message = last_messages[0].content if last_messages else None
        unread = await self.repo.get_unread_count(chat.id, current_user_id)
        members = await self.repo.get_chat_members(chat.id)
        member_responses = [
            ChatMemberResponse(user_id=m.user_id, role=m.role, joined_at=m.joined_at, is_muted=m.is_muted)
            for m in members
        ]
        return ChatResponse(
            id=chat.id, chat_type=chat.chat_type, title=chat.title,
            event_id=chat.event_id, organization_id=chat.organization_id,
            created_at=chat.created_at, updated_at=chat.updated_at,
            last_message=last_message, unread_count=unread, members=member_responses
        )

    def _message_to_response(self, message: Message) -> MessageResponse:
        return MessageResponse(
            id=message.id, chat_id=message.chat_id, sender_id=message.sender_id,
            content=message.content, message_type=message.message_type,
            attachment_url=message.attachment_url, is_read=message.is_read,
            created_at=message.created_at, updated_at=message.updated_at
        )