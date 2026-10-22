from app.services.event_service.core.chat_client import ChatServiceClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, func as sqlfunc
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

logger = logging.getLogger(__name__)

from app.services.event_service.db.models import Event, Participation, ParticipationStatus
from app.services.event_service.schemas import EventCreate, RegisterRequest


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_client = ChatServiceClient()

    async def get_events(
            self,
            org_ids: Optional[List[int]] = None,
            date_from: Optional[datetime] = None,
            limit: Optional[int] = None
    ):
        query = select(Event)
        if org_ids:
            query = query.where(Event.org_id.in_(org_ids))
        if date_from:
            query = query.where(Event.start_date >= date_from)
        if limit:
            query = query.limit(limit)
        result = await self.db.execute(query)
        events = result.scalars().all()
        return events

    async def create_event(self, event_data: EventCreate) -> Event:
        now = datetime.now(timezone.utc)
        if event_data.start_date.replace(tzinfo=timezone.utc) < now:
            raise ValueError("Нельзя создать мероприятие в прошлом")

        new_event = Event(
            org_id=event_data.org_id,
            title=event_data.title,
            description=event_data.description,
            start_date=event_data.start_date,
            end_date=event_data.end_date,
            location=event_data.location,
            max_participants=event_data.max_participants,
            qr_secret=str(uuid.uuid4())
        )
        self.db.add(new_event)
        await self.db.commit()
        await self.db.refresh(new_event)
        return new_event

    async def register_user(self, event_id: int, data: RegisterRequest) -> Participation:
        event = await self.db.get(Event, event_id)
        if not event:
            raise ValueError("Событие не найдено")

        count_res = await self.db.execute(
            select(func.count(Participation.id)).where(
                Participation.event_id == event_id,
                Participation.status != ParticipationStatus.CANCELLED
            )
        )
        current_count = count_res.scalar() or 0
        if current_count >= event.max_participants:
            raise ValueError("Лимит участников исчерпан")

        existing = await self.db.execute(
            select(Participation).where(
                Participation.event_id == event_id,
                Participation.user_id == data.user_id,
                Participation.status != ParticipationStatus.CANCELLED
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Пользователь уже зарегистрирован")

        participation = Participation(
            event_id=event_id,
            user_id=data.user_id,
            role_id=data.role_id
        )
        self.db.add(participation)
        await self.db.commit()
        await self.db.refresh(participation)

        # Асинхронно создаём/добавляем в чат мероприятия (не блокируем ответ)
        # Но для простоты выполним синхронно, с обработкой ошибок
        try:
            await self.chat_client.ensure_event_chat(
                event_id=event.id,
                user_id=data.user_id,
                organization_id=event.org_id
            )
        except Exception as e:
            # Логируем, но регистрация уже успешна
            logger.exception(f"Chat creation failed for event {event.id}")

        return participation

    async def check_in(self, event_id: int, user_id: int, qr_code: str) -> Participation:
        event = await self.db.get(Event, event_id)
        if not event:
            raise ValueError("Событие не найдено")
        if event.qr_secret != qr_code:
            raise ValueError("Неверный QR-код")

        participation = await self.db.execute(
            select(Participation).where(
                Participation.event_id == event_id,
                Participation.user_id == user_id
            )
        )
        part = participation.scalar_one_or_none()
        if not part:
            raise ValueError("Пользователь не зарегистрирован")
        if part.status == ParticipationStatus.CHECKED_IN:
            raise ValueError("Пользователь уже отметился")

        part.status = ParticipationStatus.CHECKED_IN
        part.checked_in_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(part)
        return part

    async def get_popular_events(
            self,
            exclude_org_ids: Optional[List[int]] = None,
            limit: int = 20,
            sort: Optional[str] = None,
    ) -> List[Event]:
        """
        Популярные мероприятия.
        - exclude_org_ids: исключить события указанных организаций.
        - sort='popularity': сортировка по числу регистраций (по убыванию).
          Иначе — по ближайшей дате начала.
        """
        if sort == "popularity":
            participation_count = (
                select(
                    Participation.event_id,
                    sqlfunc.count(Participation.id).label("cnt"),
                )
                .where(Participation.status != ParticipationStatus.CANCELLED)
                .group_by(Participation.event_id)
                .subquery()
            )
            stmt = (
                select(Event)
                .outerjoin(participation_count, participation_count.c.event_id == Event.id)
                .order_by(
                    sqlfunc.coalesce(participation_count.c.cnt, 0).desc(),
                    Event.start_date.asc(),
                )
            )
        else:
            stmt = select(Event).order_by(Event.start_date.asc())

        if exclude_org_ids:
            stmt = stmt.where(Event.org_id.notin_(exclude_org_ids))

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_event_by_id(self, event_id: int) -> Optional[Event]:
        return await self.db.get(Event, event_id)