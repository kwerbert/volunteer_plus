from sqlalchemy import select, update, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from .models import Chat, ChatMember, Message, ChatTypeEnum

class ChatRepository:
    """Репозиторий для операций с чатами"""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_chats_for_deletion(self, current_time: datetime) -> List[Chat]:
        stmt = select(Chat).where(
            Chat.chat_type == ChatTypeEnum.EVENT,
            Chat.is_active == True,
            Chat.scheduled_delete_at != None,
            Chat.scheduled_delete_at <= current_time
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_chat(self, chat_id: int, **kwargs) -> Optional[Chat]:
        # ✅ Убираем updated_at, если он передан — SQLAlchemy сам его проставит
        # через onupdate на колонке Chat.updated_at
        kwargs.pop("updated_at", None)
        stmt = update(Chat).where(Chat.id == chat_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_chat_by_id(chat_id)

    async def create_chat(
        self,
        chat_type: ChatTypeEnum,
        title: Optional[str] = None,
        event_id: Optional[int] = None,
        organization_id: Optional[int] = None
    ) -> Chat:
        chat = Chat(
            chat_type=chat_type, title=title,
            event_id=event_id, organization_id=organization_id
        )
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        stmt = select(Chat).where(Chat.id == chat_id, Chat.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_chats(
        self,
        user_id: int,
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> List[Chat]:
        stmt = (
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == user_id, ChatMember.left_at == None)
        )
        if active_only:
            stmt = stmt.where(Chat.is_active == True)
        stmt = stmt.order_by(Chat.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_chat(self, chat_id: int) -> bool:
        stmt = update(Chat).where(Chat.id == chat_id).values(
            is_active=False, updated_at=datetime.now(timezone.utc)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def add_member(self, chat_id: int, user_id: int, role: str = "member") -> ChatMember:
        existing = await self.get_member(chat_id, user_id)
        if existing and existing.left_at is None:
            return existing
        member = ChatMember(chat_id=chat_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def get_member(self, chat_id: int, user_id: int) -> Optional[ChatMember]:
        stmt = select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chat_members(self, chat_id: int) -> List[ChatMember]:
        stmt = select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.left_at == None
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def remove_member(self, chat_id: int, user_id: int) -> bool:
        stmt = update(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
            ChatMember.left_at == None
        ).values(left_at=datetime.now(timezone.utc))
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def update_member_role(self, chat_id: int, user_id: int, role: str) -> Optional[ChatMember]:
        stmt = update(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
        ).values(role=role)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_member(chat_id, user_id)

    async def create_message(
        self,
        chat_id: int,
        sender_id: int,
        content: str,
        message_type: str = "text",
        attachment_url: Optional[str] = None
    ) -> Message:
        message = Message(
            chat_id=chat_id, sender_id=sender_id, content=content,
            message_type=message_type, attachment_url=attachment_url
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages(
        self,
        chat_id: int,
        limit: int = 20,
        offset: int = 0,
        before_message_id: Optional[int] = None
    ) -> List[Message]:
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.desc())
        if before_message_id:
            before_msg = await self.session.get(Message, before_message_id)
            if before_msg:
                stmt = stmt.where(Message.created_at < before_msg.created_at)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def get_message_by_id(self, message_id: int) -> Optional[Message]:
        return await self.session.get(Message, message_id)

    async def mark_message_read(self, message_id: int) -> Optional[Message]:
        stmt = update(Message).where(Message.id == message_id).values(
            is_read=True, read_at=datetime.now(timezone.utc)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_message_by_id(message_id)

    async def mark_chat_messages_read(self, chat_id: int, user_id: int) -> int:
        stmt = update(Message).where(
            Message.chat_id == chat_id,
            Message.sender_id != user_id,
            Message.is_read == False
        ).values(is_read=True, read_at=datetime.now(timezone.utc))
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def get_unread_count(self, chat_id: int, user_id: int) -> int:
        stmt = select(func.count(Message.id)).where(
            Message.chat_id == chat_id,
            Message.sender_id != user_id,
            Message.is_read == False
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def user_has_access_to_chat(self, chat_id: int, user_id: int) -> bool:
        member = await self.get_member(chat_id, user_id)
        return member is not None and member.left_at is None

    async def find_organizer_chat(
            self,
            user_id: int,
            organization_id: int
    ) -> Optional[Chat]:
        """Поиск активного ORGANIZER-чата пользователя с организацией."""
        stmt = (
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(
                Chat.chat_type == ChatTypeEnum.ORGANIZER,
                Chat.organization_id == organization_id,
                Chat.is_active == True,
                ChatMember.user_id == user_id,
                ChatMember.left_at == None,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def find_personal_chat(
        self,
        user1_id: int,
        user2_id: int
    ) -> Optional[Chat]:
        """Поиск существующего личного чата (ORGANIZER) между двумя пользователями"""
        stmt = (
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(
                # ИСПРАВЛЕНО: ORGANIZER вместо PERSONAL
                Chat.chat_type == ChatTypeEnum.ORGANIZER,
                Chat.is_active == True,
                or_(
                    and_(ChatMember.user_id == user1_id, ChatMember.left_at == None),
                    and_(ChatMember.user_id == user2_id, ChatMember.left_at == None)
                )
            )
            .group_by(Chat.id)
            .having(func.count(ChatMember.id) == 2)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()