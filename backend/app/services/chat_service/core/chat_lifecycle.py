"""Жизненный цикл чатов мероприятия и синхронизация организаторов (этап 6).

Единый источник правды об организаторах — organization_organizers
(organization_service). Состав EVENT-чатов синхронизируется:
* при каждой регистрации волонтёра (ensure_event_chat, 6.1);
* при добавлении/удалении организатора организации (6.2/6.3).

Личные ORGANIZER-чаты не трогаем: приватная переписка волонтёра
с владельцем (примечание к этапу 6, консистентно с этапом 5.3).
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_service.core.organization_client import organization_client
from app.services.chat_service.db.models import Chat, ChatTypeEnum
from app.services.chat_service.db.repository import ChatRepository

logger = logging.getLogger(__name__)


async def _ensure_organizer_member(
    repo: ChatRepository, chat_id: int, user_id: int
) -> bool:
    """Организатор в чате: добавить / реактивировать / повысить роль.

    Активный участник не дублируется; "member" повышается до "organizer",
    "admin" (создатель чата) не понижается. True — если чат изменён.
    """
    member = await repo.get_member(chat_id, user_id)
    if member and member.left_at is None:
        if member.role == "member":
            await repo.update_member_role(chat_id, user_id, "organizer")
            return True
        return False
    await repo.add_member(chat_id, user_id, role="organizer")
    return True


async def ensure_event_chat(
    db: AsyncSession, event_id: int, user_id: int, organization_id: int
) -> int:
    """Создаёт event-чат (если нет), добавляет волонтёра и всех организаторов.

    Недоступность organization_service не роняет регистрацию: клиент вернёт
    [], состав досинхронизируется при следующей регистрации или при
    добавлении организатора (6.2).
    """
    repo = ChatRepository(db)
    stmt = select(Chat).where(Chat.event_id == event_id, Chat.is_active)
    result = await db.execute(stmt)
    chat = result.scalar_one_or_none()
    if not chat:
        chat = await repo.create_chat(
            chat_type=ChatTypeEnum.EVENT,
            title=f"Мероприятие #{event_id}",
            event_id=event_id,
            organization_id=organization_id,
        )
        logger.info("Created new event chat %s for event %s", chat.id, event_id)

    organizer_ids = await organization_client.get_organizer_ids(organization_id)

    # 6.1/6.4: волонтёр — "member"; организатор (в т.ч. зарегистрировавшийся
    # на своё мероприятие) — "organizer".
    if user_id in organizer_ids:
        await _ensure_organizer_member(repo, chat.id, user_id)
    else:
        await repo.add_member(chat.id, user_id, role="member")

    for organizer_id in organizer_ids:
        if organizer_id != user_id:
            await _ensure_organizer_member(repo, chat.id, organizer_id)

    return chat.id


async def add_organizer_to_org_chats(
    db: AsyncSession, organization_id: int, user_id: int
) -> int:
    """6.2: добавить организатора во все активные EVENT-чаты организации."""
    repo = ChatRepository(db)
    chats = await repo.get_org_event_chats(organization_id)
    updated = 0
    for chat in chats:
        if await _ensure_organizer_member(repo, chat.id, user_id):
            updated += 1
    logger.info(
        "Organizer %s synced to %s/%s event chats of org %s",
        user_id,
        updated,
        len(chats),
        organization_id,
    )
    return updated


async def remove_organizer_from_org_chats(
    db: AsyncSession, organization_id: int, user_id: int
) -> int:
    """6.3: убрать организатора из всех EVENT-чатов организации (left_at)."""
    repo = ChatRepository(db)
    chats = await repo.get_org_event_chats(organization_id)
    removed = 0
    for chat in chats:
        member = await repo.get_member(chat.id, user_id)
        if member and member.left_at is None:
            await repo.remove_member(chat.id, user_id)
            removed += 1
    logger.info(
        "Organizer %s removed from %s/%s event chats of org %s",
        user_id,
        removed,
        len(chats),
        organization_id,
    )
    return removed
