"""Бизнес-логика заявок на роль организатора."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service.db.models import (
    OrganizerApplication,
    OrganizerApplicationStatus,
    User,
    UserRoleEnum,
)
from app.services.user_service.db.organizer_application_repository import (
    OrganizerApplicationRepository,
)
from app.services.user_service.db.repository import UserRepository

logger = logging.getLogger(__name__)

# Повторная подача после отклонения — не раньше чем через час
REJECTION_COOLDOWN = timedelta(hours=1)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite DateTime отдаёт naive-datetime (даже если писали aware UTC).
    Приводим всё к aware UTC, иначе сравнение дат упадёт с TypeError."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class OrganizerApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.applications = OrganizerApplicationRepository(session)
        self.users = UserRepository(session)

    # === Волонтёр ===

    async def create_application(self, current_user: User) -> OrganizerApplication:
        # 1. Только VOLUNTEER
        if current_user.role == UserRoleEnum.ORGANIZER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь уже является организатором",
            )
        if current_user.role != UserRoleEnum.VOLUNTEER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Заявку может подать только волонтёр (текущая роль: {current_user.role})",
            )

        # 2. Активная заявка → 409
        pending = await self.applications.get_pending_for_user(current_user.id)
        if pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Заявка уже на рассмотрении (id={pending.id})",
            )

        # 3. Кулдаун после отклонения → 429
        last_rejected = await self.applications.get_last_rejected_for_user(current_user.id)
        if last_rejected is not None:
            rejected_at = _as_utc(last_rejected.reviewed_at) or _as_utc(
                last_rejected.created_at
            )
            now = datetime.now(timezone.utc)
            retry_at = rejected_at + REJECTION_COOLDOWN
            if now < retry_at:
                retry_after = int((retry_at - now).total_seconds()) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Заявка была отклонена менее часа назад",
                        "rejected_at": rejected_at.isoformat(),
                        "retry_at": retry_at.isoformat(),
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        # 4. Создание
        application = await self.applications.create(current_user.id)
        try:
            await self.session.commit()
        except IntegrityError:
            # сработал partial unique index — параллельный запрос уже создал pending
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Заявка уже на рассмотрении",
            )
        await self.session.refresh(application)
        logger.info("Organizer application %s created by user %s", application.id, current_user.id)
        return application

    async def get_my_latest(self, user_id: int) -> OrganizerApplication:
        application = await self.applications.get_latest_for_user(user_id)
        if application is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заявка не найдена",
            )
        return application

    # === Админ ===

    async def review_application(
        self,
        application_id: int,
        admin: User,
        new_status: OrganizerApplicationStatus,
        rejection_reason: Optional[str] = None,
    ) -> OrganizerApplication:
        application = await self.applications.get_by_id(application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        if application.status != OrganizerApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Заявка уже рассмотрена (status={application.status.value})",
            )

        if application.user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя рассматривать собственную заявку",
            )

        applicant = await self.users.get_by_id(application.user_id)
        if applicant is None or not applicant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден или деактивирован",
            )

        now = datetime.now(timezone.utc)

        if new_status == OrganizerApplicationStatus.APPROVED:
            applicant.role = UserRoleEnum.ORGANIZER   # объект в той же сессии
            application.status = OrganizerApplicationStatus.APPROVED
            application.rejection_reason = None
        else:
            application.status = OrganizerApplicationStatus.REJECTED
            application.rejection_reason = (rejection_reason or "").strip() or None

        application.reviewed_by = admin.id
        application.reviewed_at = now

        await self.session.commit()
        await self.session.refresh(application)
        logger.info(
            "Organizer application %s -> %s by admin %s",
            application.id, application.status.value, admin.id,
        )
        return application