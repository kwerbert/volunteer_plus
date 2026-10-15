from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.chat_service.db.models import Chat, ChatMember, ChatTypeEnum
from app.services.chat_service.db.repository import ChatRepository
import logging

logger = logging.getLogger(__name__)

async def ensure_event_chat(
    db: AsyncSession,
    event_id: int,
    user_id: int,
    organization_id: int
) -> int:
    """
    Создаёт event-чат, если он не существует, и добавляет пользователя.
    Возвращает chat_id.
    """
    repo = ChatRepository(db)
    # Ищем чат по event_id
    stmt = select(Chat).where(Chat.event_id == event_id, Chat.is_active == True)
    result = await db.execute(stmt)
    chat = result.scalar_one_or_none()

    if not chat:
        # Создаём новый чат
        chat = await repo.create_chat(
            chat_type=ChatTypeEnum.EVENT,
            title=f"Мероприятие #{event_id}",
            event_id=event_id,
            organization_id=organization_id
        )
        logger.info(f"Created new event chat {chat.id} for event {event_id}")

    # Добавляем пользователя, если ещё не участник
    existing_member = await repo.get_member(chat.id, user_id)
    if not existing_member or existing_member.left_at is not None:
        await repo.add_member(chat.id, user_id, role="member")
        logger.info(f"Added user {user_id} to chat {chat.id}")
    else:
        logger.info(f"User {user_id} already in chat {chat.id}")

    return chat.id