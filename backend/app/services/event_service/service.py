import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service.config import settings
from app.services.event_service.core.analytics_client import AnalyticsServiceClient
from app.services.event_service.core.chat_client import ChatServiceClient
from app.services.event_service.core.notification_client import (
    NotificationServiceClient,
)
from app.services.event_service.core.organization_client import (
    OrganizationServiceClient,
)
from app.services.event_service.core.user_client import UserServiceClient
from app.services.event_service.db.models import (
    Event,
    EventRole,
    EventStatus,
    Participation,
    ParticipationStatus,
)
from app.services.event_service.schemas import (
    EventCancelResponse,
    EventCleanupResponse,
    EventCreate,
    EventResponse,
    EventRoleResponse,
    EventUpdate,
    OrganizationEventsCancelResponse,
    ParticipationRoleInfoResponse,
    RegisterRequest,
)
from app.utils.notifications_enums import NotificationType, Priority

logger = logging.getLogger(__name__)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite отдаёт naive-datetime, даже если писали aware UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utcnow_naive() -> datetime:
    """Параметры сравнения в SQL приводим к виду, в котором SQLite хранит даты
    (UTC без смещения), иначе строковое сравнение дат врёт."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_client = ChatServiceClient()
        self.org_client = OrganizationServiceClient()
        self.user_client = UserServiceClient()
        self.notification_client = NotificationServiceClient()
        self.analytics_client = AnalyticsServiceClient()

    # === Права (этап 3.1 + 4.2) ===
    async def _require_org_organizer(self, org_id: int, user_id: int) -> None:
        if not await self.org_client.is_organizer(org_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только организатор организации может управлять мероприятиями",
            )

    async def _require_event_manager(self, org_id: int, user_id: int) -> None:
        """4.2: организатор организации ИЛИ is_admin."""
        try:
            if await self.org_client.is_organizer(org_id, user_id):
                return
        except HTTPException as e:
            # Организация удалена/не найдена — админ всё равно должен иметь доступ.
            if e.status_code != status.HTTP_404_NOT_FOUND:
                raise
        if await self.user_client.is_admin(user_id):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Действие доступно организатору организации или администратору",
        )

    # === Жизненный цикл: завершение (4.4) ===
    @staticmethod
    def _is_over(event: Event) -> bool:
        end = _as_utc(event.end_date) or _as_utc(event.start_date)
        return end is not None and end <= datetime.now(timezone.utc)

    async def _sync_completion(self, event: Event) -> bool:
        """Ленивая проверка при запросе: active + end_date прошёл → completed."""
        if event.status == EventStatus.ACTIVE.value and self._is_over(event):
            event.status = EventStatus.COMPLETED.value
            await self.db.flush()
            logger.info("Event %s auto-completed (end_date passed)", event.id)
            await self._credit_hours_for_completed([event])
            return True
        return False

    async def complete_expired_events(self, org_ids: Optional[List[int]] = None) -> int:
        now_naive = _utcnow_naive()
        stmt = select(Event).where(
            Event.status == EventStatus.ACTIVE.value,
            or_(
                Event.end_date <= now_naive,
                Event.end_date.is_(None) & (Event.start_date <= now_naive),
            ),
        )
        if org_ids:
            stmt = stmt.where(Event.org_id.in_(org_ids))
        events = list((await self.db.execute(stmt)).scalars().all())
        completed: List[Event] = []
        for event in events:
            if self._is_over(event):
                event.status = EventStatus.COMPLETED.value
                completed.append(event)
        if completed:
            await self.db.commit()
            logger.info("Completed %s expired events", len(completed))
            await self._credit_hours_for_completed(completed)
        return len(completed)

    # === Чтение ===
    async def get_events(
        self,
        org_ids: Optional[List[int]] = None,
        date_from: Optional[datetime] = None,
        limit: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> List[EventResponse]:
        query = select(Event)
        if status_filter is None:
            query = query.where(Event.status == EventStatus.ACTIVE.value)
        elif status_filter != "all":
            query = query.where(Event.status == status_filter)
        if org_ids:
            query = query.where(Event.org_id.in_(org_ids))
        if date_from:
            query = query.where(Event.start_date >= date_from)
        if limit:
            query = query.limit(limit)

        events = list((await self.db.execute(query)).scalars().all())
        completed_events: List[Event] = []
        for event in events:
            if event.status == EventStatus.ACTIVE.value and self._is_over(event):
                event.status = EventStatus.COMPLETED.value
                completed_events.append(event)
        if completed_events:
            await self.db.flush()
            await self._credit_hours_for_completed(completed_events)
        if status_filter is None:
            events = [e for e in events if e.status == EventStatus.ACTIVE.value]
        return [EventResponse.model_validate(e) for e in events]

    async def get_event_detail(self, event_id: int) -> Optional[EventResponse]:
        event = await self.db.get(Event, event_id)
        if not event:
            return None
        await self._sync_completion(event)
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

    # === Создание (этап 3) ===
    async def create_event(
        self, event_data: EventCreate, current_user_id: int
    ) -> EventResponse:
        now = datetime.now(timezone.utc)
        if event_data.start_date.replace(tzinfo=timezone.utc) < now:
            raise ValueError("Нельзя создать мероприятие в прошлом")
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

    # === Редактирование ===
    async def update_event(
        self, event_id: int, data: EventUpdate, current_user_id: int
    ) -> EventResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        await self._require_org_organizer(event.org_id, current_user_id)
        await self._sync_completion(event)
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

    # === Отмена мероприятия (4.2 / 4.5) ===
    async def cancel_event(
        self, event_id: int, current_user_id: int
    ) -> EventCancelResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        await self._require_event_manager(event.org_id, current_user_id)
        await self._sync_completion(event)

        if event.status == EventStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Завершённое мероприятие нельзя отменить или удалить",
            )
        if event.status == EventStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Мероприятие уже отменено",
            )

        recipients, cancelled_count = await self._cancel_event_record(event)
        await self.db.commit()
        logger.info(
            "Event %s cancelled by user %s (participations=%s, notify=%s)",
            event_id,
            current_user_id,
            cancelled_count,
            len(recipients),
        )
        self._notify_event_cancelled(event, recipients)
        # Этап 5: организаторы тоже узнают об отмене (инициатору не шлём).
        await self._notify_organizers(
            org_id=event.org_id,
            title="Мероприятие отменено",
            body=f'Мероприятие "{event.title}" отменено',
            notification_type=NotificationType.EVENT_CANCELLED,
            priority=Priority.HIGH,
            data={"event_id": event.id, "org_id": event.org_id},
            exclude_user_id=current_user_id,
        )
        return EventCancelResponse(
            id=event.id,
            status=event.status,
            cancelled_at=_as_utc(event.cancelled_at),
            cancelled_participations=cancelled_count,
            notified_volunteers=len(recipients),
        )

    async def _cancel_event_record(self, event: Event) -> Tuple[List[int], int]:
        """Мутация без commit: получатели собираются ДО отмены регистраций."""
        recipients = await self._registered_user_ids(event.id)
        result = await self.db.execute(
            update(Participation)
            .where(
                Participation.event_id == event.id,
                Participation.status == ParticipationStatus.REGISTERED,
            )
            .values(status=ParticipationStatus.CANCELLED)
        )
        event.status = EventStatus.CANCELLED.value
        event.cancelled_at = datetime.now(timezone.utc)
        return recipients, result.rowcount or 0

    # === Уведомления организаторам (этап 5) ===

    async def _organizer_ids(
        self, org_id: int, exclude_user_id: Optional[int] = None
    ) -> List[int]:
        """Организаторы организации — получатели уведомлений.

        Недоступность organization_service не должна ронять бизнес-операцию:
        уведомление — побочный эффект, регистрация/отмена важнее.
        """
        try:
            organizers = await self.org_client.get_organizers(org_id)
        except Exception:
            logger.warning(
                "Cannot fetch organizers of org %s for notifications", org_id
            )
            return []
        return sorted(
            {
                int(o["user_id"])
                for o in organizers
                if int(o["user_id"]) != exclude_user_id
            }
        )

    async def _notify_organizers(
        self,
        org_id: int,
        *,
        title: str,
        body: str,
        notification_type: NotificationType,
        data: Dict,
        exclude_user_id: Optional[int] = None,
        priority: Priority = Priority.NORMAL,
    ) -> int:
        recipients = await self._organizer_ids(org_id, exclude_user_id)
        if not recipients:
            return 0
        self.notification_client.notify_background(
            user_ids=recipients,
            title=title,
            body=body,
            notification_type=notification_type,
            priority=priority,
            data=data,
        )
        return len(recipients)

    def _notify_event_cancelled(self, event: Event, recipients: List[int]) -> None:
        """4.5: «Мероприятие "{название}" отменено» каждому зарегистрированному."""
        if not recipients:
            return
        self.notification_client.notify_background(
            user_ids=recipients,
            title="Мероприятие отменено",
            body=f'Мероприятие "{event.title}" отменено',
            notification_type=NotificationType.EVENT_CANCELLED,
            priority=Priority.HIGH,
            data={"event_id": event.id, "org_id": event.org_id},
        )

    # === Удаление организации → отмена её мероприятий (4.6) ===
    async def cancel_organization_events(
        self, org_id: int
    ) -> OrganizationEventsCancelResponse:
        # Просроченные сначала завершаем: завершённые отменять нельзя.
        completed = await self.complete_expired_events(org_ids=[org_id])
        result = await self.db.execute(
            select(Event).where(
                Event.org_id == org_id,
                Event.status == EventStatus.ACTIVE.value,
            )
        )
        events = list(result.scalars().all())
        pending_notifications: List[Tuple[Event, List[int]]] = []
        cancelled_participations = 0
        notified = 0
        for event in events:
            recipients, count = await self._cancel_event_record(event)
            cancelled_participations += count
            notified += len(recipients)
            pending_notifications.append((event, recipients))
        await self.db.commit()
        for event, recipients in pending_notifications:
            self._notify_event_cancelled(event, recipients)

        # Организаторам — одно агрегированное уведомление, а не N штук.
        if events:
            await self._notify_organizers(
                org_id=org_id,
                title="Мероприятия отменены",
                body=f"Организация удалена: отменено мероприятий — {len(events)}",
                notification_type=NotificationType.EVENT_CANCELLED,
                priority=Priority.HIGH,
                data={"org_id": org_id, "cancelled_events": len(events)},
            )
        logger.info(
            "Organization %s: cancelled %s events (%s participations), completed %s",
            org_id,
            len(events),
            cancelled_participations,
            completed,
        )
        return OrganizationEventsCancelResponse(
            organization_id=org_id,
            cancelled_events=len(events),
            cancelled_participations=cancelled_participations,
            notified_volunteers=notified,
            completed_events=completed,
        )

    async def _credit_hours_for_completed(self, events: List[Event]) -> None:
        """Триггер аналитики: при переходе active→completed начисляем часы
        волонтёрам со статусом CHECKED_IN (отметка о посещении). Аналитика
        сама возьмёт hours_value и name роли из event_roles (этап 8.1/8.2).
        Побочный эффект: fire-and-forget, сбой analytics не роняет завершение.
        Гард от задвоения — сам переход статуса (completed не завершается повторно)."""
        if not settings.ANALYTICS_TRIGGER_ENABLED:
            return
        for event in events:
            user_ids = await self._checked_in_user_ids(event.id)
            if user_ids:
                self.analytics_client.complete_background(event.id, user_ids)

    async def _checked_in_user_ids(self, event_id: int) -> List[int]:
        result = await self.db.execute(
            select(Participation.user_id).where(
                Participation.event_id == event_id,
                Participation.status == ParticipationStatus.CHECKED_IN,
            )
        )
        return sorted({row[0] for row in result.fetchall()})

    async def get_participation_role_info(
        self, event_id: int, user_id: int
    ) -> Optional[ParticipationRoleInfoResponse]:
        """Этап 8.1: регистрация + роль для analytics_service (internal API).
        None — мероприятие/регистрация не найдены (роутер отдаст 404).
        Роль удалена → role_name/hours_value = None → дефолт на стороне аналитики."""
        event = await self.db.get(Event, event_id)
        if not event:
            return None
        result = await self.db.execute(
            select(Participation)
            .where(
                Participation.event_id == event_id,
                Participation.user_id == user_id,
                Participation.status != ParticipationStatus.CANCELLED,
            )
            .order_by(Participation.id.desc())
        )
        part = result.scalars().first()
        if part is None:
            return None

        role_name: Optional[str] = None
        hours_value: Optional[float] = None
        if part.role_id is not None:
            role = await self.db.get(EventRole, part.role_id)
            if role is not None and role.event_id == event_id:
                role_name = role.name
                hours_value = role.hours_value

        status_value = (
            part.status.value
            if isinstance(part.status, ParticipationStatus)
            else str(part.status)
        )
        return ParticipationRoleInfoResponse(
            event_id=event_id,
            user_id=user_id,
            status=status_value,
            role_id=part.role_id,
            role_name=role_name,
            hours_value=hours_value,
        )

    # === Автоочистка отменённых (4.3) ===
    async def cleanup_cancelled_events(
        self, retention_days: Optional[int] = None
    ) -> EventCleanupResponse:
        days = (
            retention_days
            if retention_days is not None
            else settings.CANCELLED_RETENTION_DAYS
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        ids = [
            row[0]
            for row in (
                await self.db.execute(
                    select(Event.id).where(
                        Event.status == EventStatus.CANCELLED.value,
                        Event.cancelled_at.isnot(None),
                        Event.cancelled_at <= cutoff.replace(tzinfo=None),
                    )
                )
            ).fetchall()
        ]
        deleted_participations = deleted_roles = deleted_events = 0
        if ids:
            # Порядок важен: сначала дочерние записи, потом само мероприятие.
            deleted_participations = (
                await self.db.execute(
                    delete(Participation).where(Participation.event_id.in_(ids))
                )
            ).rowcount or 0
            deleted_roles = (
                await self.db.execute(
                    delete(EventRole).where(EventRole.event_id.in_(ids))
                )
            ).rowcount or 0
            deleted_events = (
                await self.db.execute(delete(Event).where(Event.id.in_(ids)))
            ).rowcount or 0
            await self.db.commit()
            logger.info(
                "Cleanup: deleted %s cancelled events (retention=%s days, ids=%s)",
                deleted_events,
                days,
                ids,
            )
        # completed не удаляются никогда (4.3/4.4) — они в статистике.
        return EventCleanupResponse(
            deleted_events=deleted_events,
            deleted_participations=deleted_participations,
            deleted_roles=deleted_roles,
            retention_days=days,
            cutoff=cutoff,
        )

    # === Регистрация (4.1) ===
    async def register_user(
        self, event_id: int, data: RegisterRequest
    ) -> Participation:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        await self._sync_completion(event)
        if event.status != EventStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Мероприятие недоступно для регистрации",
            )

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
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь уже зарегистрирован",
            )

        roles = await self._get_roles(event_id)
        if not roles:
            role = self._add_default_role(event_id)
            await self.db.flush()
            roles = [role]

        role_id = data.event_role_id  # алиас role_id синхронизирован схемой
        if role_id is not None:
            role = next((r for r in roles if r.id == role_id), None)
            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Роль не принадлежит этому мероприятию",
                )
        else:
            if event.has_custom_roles:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Необходимо выбрать роль",
                )
            role = roles[0]

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
        # Этап 5.2: NEW_REGISTRATION всем организаторам организации.
        # Себе не шлём (организатор может зарегистрироваться сам).
        await self._notify_organizers(
            org_id=event.org_id,
            title="Новая регистрация",
            body=f'Волонтёр записался на "{event.title}" — роль «{role.name}»',
            notification_type=NotificationType.NEW_REGISTRATION,
            data={
                "event_id": event.id,
                "org_id": event.org_id,
                "user_id": data.user_id,
                "event_role_id": role.id,
            },
            exclude_user_id=data.user_id,
        )
        return participation

    async def unregister_user(self, event_id: int, user_id: int) -> Participation:
        """Отмена регистрации волонтёром (освобождает место на роли)."""
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        await self._sync_completion(event)
        if event.status == EventStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Мероприятие уже завершено — регистрация в истории",
            )
        result = await self.db.execute(
            select(Participation)
            .where(
                Participation.event_id == event_id,
                Participation.user_id == user_id,
                Participation.status != ParticipationStatus.CANCELLED,
            )
            .order_by(Participation.id.desc())
        )
        participation = result.scalars().first()
        if participation is None:
            raise HTTPException(status_code=404, detail="Регистрация не найдена")
        if participation.status == ParticipationStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя отменить регистрацию после отметки о посещении",
            )
        participation.status = ParticipationStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(participation)
        logger.info("User %s cancelled registration for event %s", user_id, event_id)
        # Этап 5.2: REGISTRATION_CANCELLED всем организаторам организации.
        role_name = None
        if participation.role_id:
            roles = await self._get_roles(event_id)
            role = next((r for r in roles if r.id == participation.role_id), None)
            role_name = role.name if role else None

        body = f'Волонтёр отменил регистрацию на "{event.title}"'
        if role_name:
            body += f" — роль «{role_name}»"

        await self._notify_organizers(
            org_id=event.org_id,
            title="Отмена регистрации",
            body=body,
            notification_type=NotificationType.REGISTRATION_CANCELLED,
            data={
                "event_id": event.id,
                "org_id": event.org_id,
                "user_id": user_id,
                "event_role_id": participation.role_id,
            },
            exclude_user_id=user_id,
        )
        return participation

    # === Чекин ===
    async def check_in(
        self, event_id: int, user_id: int, qr_code: Optional[str]
    ) -> Participation:
        event = await self.db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        if event.status == EventStatus.CANCELLED.value:
            raise ValueError("Мероприятие отменено")
        if event.qr_check_enabled and event.qr_secret != qr_code:
            raise ValueError("Неверный QR-код")

        result = await self.db.execute(
            select(Participation)
            .where(
                Participation.event_id == event_id,
                Participation.user_id == user_id,
                Participation.status != ParticipationStatus.CANCELLED,
            )
            .order_by(Participation.id.desc())
        )
        part = result.scalars().first()
        if not part:
            raise ValueError("Пользователь не зарегистрирован")
        if part.status == ParticipationStatus.CHECKED_IN:
            raise ValueError("Пользователь уже отметился")
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

    async def _registered_user_ids(self, event_id: int) -> List[int]:
        result = await self.db.execute(
            select(Participation.user_id).where(
                Participation.event_id == event_id,
                Participation.status != ParticipationStatus.CANCELLED,
            )
        )
        return sorted({row[0] for row in result.fetchall()})

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
