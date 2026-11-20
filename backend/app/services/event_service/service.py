import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service.config import settings
from app.services.event_service.core.chat_client import ChatServiceClient
from app.services.event_service.core.organization_client import (
    OrganizationServiceClient,
)
from app.services.event_service.db.models import (
    Event,
    EventRole,
    EventStatus,
    Participation,
    ParticipationStatus,
)
from app.services.event_service.schemas import (
    EventCreate,
    EventResponse,
    EventRoleResponse,
    EventUpdate,
    RegisterRequest,
)

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_client = ChatServiceClient()
        self.org_client = OrganizationServiceClient()

    # === Права (этап 3.1) ===
    async def _require_org_organizer(self, org_id: int, user_id: int) -> None:
        if not await self.org_client.is_organizer(org_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только организатор организации может управлять мероприятиями",
            )

    # === Чтение ===
    async def get_events(
        self,
        org_ids: Optional[List[int]] = None,
        date_from: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[EventResponse]:
        query = select(Event).where(Event.status == EventStatus.ACTIVE.value)
        if org_ids:
            query = query.where(Event.org_id.in_(org_ids))
        if date_from:
            query = query.where(Event.start_date >= date_from)
        if limit:
            query = query.limit(limit)
        result = await self.db.execute(query)
        # Список/лента: без ролей (роли — в детальном GET, этап 3.7)
        return [EventResponse.model_validate(e) for e in result.scalars().all()]

    async def get_event_detail(self, event_id: int) -> Optional[EventResponse]:
        event = await self.db.get(Event, event_id)
        if not event:
            return None
        roles = await self._get_roles(event_id)
        counts = await self._role_registered_counts(event_id)
        return self._build_response(event, roles, counts)

    async def get_popular_events(
        self,
        exclude_org_ids: Optional[List[int]] = None,
        limit: int = 20,
        sort: Optional[str] = None,
    ) -> List[EventResponse]:
        if sort == "popularity":
            participation_count = (
                select(
                    Participation.event_id,
                    func.count(Participation.id).label("cnt"),
                )
                .where(Participation.status != ParticipationStatus.CANCELLED)
                .group_by(Participation.event_id)
                .subquery()
            )
            stmt = (
                select(Event)
                .outerjoin(
                    participation_count, participation_count.c.event_id == Event.id
                )
                .where(Event.status == EventStatus.ACTIVE.value)
                .order_by(
                    func.coalesce(participation_count.c.cnt, 0).desc(),
                    Event.start_date.asc(),
                )
            )
        else:
            stmt = (
                select(Event)
                .where(Event.status == EventStatus.ACTIVE.value)
                .order_by(Event.start_date.asc())
            )
        if exclude_org_ids:
            stmt = stmt.where(Event.org_id.notin_(exclude_org_ids))
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return [EventResponse.model_validate(e) for e in result.scalars().all()]

    # === Создание (этап 3.1/3.3/3.4/3.6) ===
    async def create_event(
        self, event_data: EventCreate, current_user_id: int
    ) -> EventResponse:
        now = datetime.now(timezone.utc)
        if event_data.start_date.replace(tzinfo=timezone.utc) < now:
            raise ValueError("Нельзя создать мероприятие в прошлом")

        # Право = членство в organization_organizers (403/404/503 из клиента)
        await self._require_org_organizer(event_data.org_id, current_user_id)

        has_custom_roles = bool(event_data.roles)
        new_event = Event(
            org_id=event_data.org_id,
            title=event_data.title,
            description=event_data.description,
            start_date=event_data.start_date,
            end_date=event_data.end_date,
            location=event_data.location,
            max_participants=event_data.max_participants,
            qr_secret=str(uuid.uuid4()),
            qr_check_enabled=event_data.qr_check_enabled,
            image_url=event_data.image_url,
            status=EventStatus.ACTIVE.value,
            has_custom_roles=has_custom_roles,
        )
        self.db.add(new_event)
        await self.db.flush()

        if has_custom_roles:
            for role in event_data.roles:
                self.db.add(
                    EventRole(
                        event_id=new_event.id,
                        name=role.name,
                        description=role.description,
                        hours_value=role.hours_value,
                        max_participants=role.max_participants,
                    )
                )
        else:
            self._add_default_role(new_event.id)

        await self.db.commit()
        await self.db.refresh(new_event)

        logger.info(
            "Event %s created by user %s (org %s, custom_roles=%s)",
            new_event.id,
            current_user_id,
            new_event.org_id,
            has_custom_roles,
        )
        roles = await self._get_roles(new_event.id)
        return self._build_response(new_event, roles, {})

    # === Редактирование (этап 3.1) ===
    async def update_event(
        self, event_id: int, data: EventUpdate, current_user_id: int
    ) -> EventResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        await self._require_org_organizer(event.org_id, current_user_id)
        if event.status != EventStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя редактировать отменённое или завершённое мероприятие",
            )
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(event, field, value)
        await self.db.commit()
        logger.info("Event %s updated by user %s", event_id, current_user_id)
        return await self.get_event_detail(event_id)

    # === Регистрация (этап 3.5 + лимит по роли) ===
    async def register_user(
        self, event_id: int, data: RegisterRequest
    ) -> Participation:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        if event.status != EventStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Мероприятие недоступно для регистрации",
            )

        # Общий лимит мероприятия
        count_res = await self.db.execute(
            select(func.count(Participation.id)).where(
                Participation.event_id == event_id,
                Participation.status != ParticipationStatus.CANCELLED,
            )
        )
        if (count_res.scalar() or 0) >= event.max_participants:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Лимит участников исчерпан"
            )

        existing = await self.db.execute(
            select(Participation).where(
                Participation.event_id == event_id,
                Participation.user_id == data.user_id,
                Participation.status != ParticipationStatus.CANCELLED,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь уже зарегистрирован",
            )

        roles = await self._get_roles(event_id)
        if not roles:
            # Защита для старых данных до этапа 3: дефолтная роль на лету
            role = self._add_default_role(event_id)
            await self.db.flush()
            roles = [role]

        if data.role_id is not None:
            role = next((r for r in roles if r.id == data.role_id), None)
            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Роль не принадлежит этому мероприятию",
                )
        else:
            if event.has_custom_roles:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Необходимо выбрать роль",
                )
            role = roles[0]  # одна дефолтная — подставляем автоматически

        # Лимит по конкретной роли (этап 3, вопрос реализации) → 409
        if role.max_participants is not None:
            role_count = await self.db.execute(
                select(func.count(Participation.id)).where(
                    Participation.event_id == event_id,
                    Participation.role_id == role.id,
                    Participation.status != ParticipationStatus.CANCELLED,
                )
            )
            if (role_count.scalar() or 0) >= role.max_participants:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Все места на роль «{role.name}» заняты",
                )

        participation = Participation(
            event_id=event_id, user_id=data.user_id, role_id=role.id
        )
        self.db.add(participation)
        await self.db.commit()
        await self.db.refresh(participation)

        try:
            await self.chat_client.ensure_event_chat(
                event_id=event.id, user_id=data.user_id, organization_id=event.org_id
            )
        except Exception:
            logger.exception("Chat creation failed for event %s", event.id)

        logger.info(
            "User %s registered for event %s (role %s)",
            data.user_id,
            event_id,
            role.id,
        )
        return participation

    # === Чекин (учитываем qr_check_enabled, этап 3.4) ===
    async def check_in(
        self, event_id: int, user_id: int, qr_code: Optional[str]
    ) -> Participation:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        if event.qr_check_enabled and event.qr_secret != qr_code:
            raise ValueError("Неверный QR-код")

        participation = await self.db.execute(
            select(Participation).where(
                Participation.event_id == event_id, Participation.user_id == user_id
            )
        )
        part = participation.scalar_one_or_none()
        if not part:
            raise ValueError("Пользователь не зарегистрирован")
        if part.status == ParticipationStatus.CHECKED_IN:
            raise ValueError("Пользователь уже отметился")
        if part.status == ParticipationStatus.CANCELLED:
            raise ValueError("Регистрация отменена")

        part.status = ParticipationStatus.CHECKED_IN
        part.checked_in_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(part)
        return part

    # === Helpers ===
    def _add_default_role(self, event_id: int) -> EventRole:
        role = EventRole(
            event_id=event_id,
            name=settings.DEFAULT_ROLE_NAME,
            hours_value=settings.DEFAULT_EVENT_HOURS,
            max_participants=None,
        )
        self.db.add(role)
        return role

    async def _get_roles(self, event_id: int) -> List[EventRole]:
        result = await self.db.execute(
            select(EventRole)
            .where(EventRole.event_id == event_id)
            .order_by(EventRole.id)
        )
        return list(result.scalars().all())

    async def _role_registered_counts(self, event_id: int) -> Dict[int, int]:
        result = await self.db.execute(
            select(Participation.role_id, func.count(Participation.id))
            .where(
                Participation.event_id == event_id,
                Participation.status != ParticipationStatus.CANCELLED,
                Participation.role_id.isnot(None),
            )
            .group_by(Participation.role_id)
        )
        return {role_id: cnt for role_id, cnt in result.fetchall()}

    @staticmethod
    def _build_response(
        event: Event, roles: List[EventRole], counts: Dict[int, int]
    ) -> EventResponse:
        return EventResponse(
            id=event.id,
            org_id=event.org_id,
            title=event.title,
            description=event.description,
            start_date=event.start_date,
            end_date=event.end_date,
            location=event.location,
            max_participants=event.max_participants,
            qr_check_enabled=event.qr_check_enabled,
            status=event.status,
            image_url=event.image_url,
            cancelled_at=event.cancelled_at,
            has_custom_roles=event.has_custom_roles,
            roles=[
                EventRoleResponse(
                    id=r.id,
                    event_id=r.event_id,
                    name=r.name,
                    description=r.description,
                    hours_value=r.hours_value,
                    max_participants=r.max_participants,
                    registered_count=counts.get(r.id, 0),
                )
                for r in roles
            ],
        )
