"""Репозиторий заявок на роль организатора."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service.db.models import (
    OrganizerApplication,
    OrganizerApplicationStatus,
)


class OrganizerApplicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, application_id: int) -> Optional[OrganizerApplication]:
        stmt = select(OrganizerApplication).where(
            OrganizerApplication.id == application_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_latest_for_user(self, user_id: int) -> Optional[OrganizerApplication]:
        stmt = (
            select(OrganizerApplication)
            .where(OrganizerApplication.user_id == user_id)
            .order_by(
                OrganizerApplication.created_at.desc(), OrganizerApplication.id.desc()
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_pending_for_user(
        self, user_id: int
    ) -> Optional[OrganizerApplication]:
        stmt = select(OrganizerApplication).where(
            OrganizerApplication.user_id == user_id,
            OrganizerApplication.status == OrganizerApplicationStatus.PENDING,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_last_rejected_for_user(
        self, user_id: int
    ) -> Optional[OrganizerApplication]:
        """Последняя отклонённая заявка (по дате рассмотрения, fallback — created_at)."""
        reviewed_or_created = func.coalesce(
            OrganizerApplication.reviewed_at, OrganizerApplication.created_at
        )
        stmt = (
            select(OrganizerApplication)
            .where(
                OrganizerApplication.user_id == user_id,
                OrganizerApplication.status == OrganizerApplicationStatus.REJECTED,
            )
            .order_by(reviewed_or_created.desc(), OrganizerApplication.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, user_id: int) -> OrganizerApplication:
        application = OrganizerApplication(
            user_id=user_id,
            status=OrganizerApplicationStatus.PENDING,
        )
        self.session.add(application)
        await self.session.flush()
        return application

    async def list_by_status(
        self,
        status: Optional[OrganizerApplicationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OrganizerApplication]:
        """Задел под админ-панель (эндпоинт пока не входит в Этап 1)."""
        stmt = select(OrganizerApplication)
        if status is not None:
            stmt = stmt.where(OrganizerApplication.status == status)
        stmt = (
            stmt.order_by(OrganizerApplication.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())
