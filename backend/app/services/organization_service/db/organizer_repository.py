"""Репозиторий связей «организация ↔ организаторы».
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Organization, OrganizationOrganizer, OrgOrganizerRole


class OrganizationOrganizerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_membership(
        self, organization_id: int, user_id: int
    ) -> Optional[OrganizationOrganizer]:
        """Любая запись, включая мягко удалённые (для реактивации)."""
        stmt = select(OrganizationOrganizer).where(
            OrganizationOrganizer.organization_id == organization_id,
            OrganizationOrganizer.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_active_membership(
        self, organization_id: int, user_id: int
    ) -> Optional[OrganizationOrganizer]:
        stmt = select(OrganizationOrganizer).where(
            OrganizationOrganizer.organization_id == organization_id,
            OrganizationOrganizer.user_id == user_id,
            OrganizationOrganizer.is_active,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_active_by_organization(
        self, organization_id: int
    ) -> List[OrganizationOrganizer]:
        # Владелец добавляется при создании организации → естественно первый.
        stmt = (
            select(OrganizationOrganizer)
            .where(
                OrganizationOrganizer.organization_id == organization_id,
                OrganizationOrganizer.is_active,
            )
            .order_by(OrganizationOrganizer.added_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_owned_organization_id(self, user_id: int) -> Optional[int]:
        """Id организации, которой пользователь активно владеет (или None)."""
        stmt = select(OrganizationOrganizer.organization_id).where(
            OrganizationOrganizer.user_id == user_id,
            OrganizationOrganizer.role_in_org == OrgOrganizerRole.OWNER,
            OrganizationOrganizer.is_active,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def is_owner(self, organization_id: int, user_id: int) -> bool:
        membership = await self.get_active_membership(organization_id, user_id)
        return (
            membership is not None and membership.role_in_org == OrgOrganizerRole.OWNER
        )

    async def add(
        self,
        organization_id: int,
        user_id: int,
        role_in_org: OrgOrganizerRole,
        added_by: int,
    ) -> OrganizationOrganizer:
        membership = OrganizationOrganizer(
            organization_id=organization_id,
            user_id=user_id,
            role_in_org=role_in_org,
            added_by=added_by,
            is_active=True,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def reactivate(
        self, membership: OrganizationOrganizer, added_by: int
    ) -> OrganizationOrganizer:
        """Повторное добавление после мягкого удаления."""
        membership.role_in_org = OrgOrganizerRole.ORGANIZER
        membership.added_by = added_by
        membership.added_at = datetime.now(timezone.utc)
        membership.is_active = True
        await self.session.flush()
        return membership

    async def deactivate(self, membership: OrganizationOrganizer) -> None:
        membership.is_active = False
        await self.session.flush()

    async def deactivate_all_for_organization(self, organization_id: int) -> int:
        stmt = (
            update(OrganizationOrganizer)
            .where(
                OrganizationOrganizer.organization_id == organization_id,
                OrganizationOrganizer.is_active,
            )
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_active_organization_ids(self, user_id: int) -> List[int]:
        """Организации, где пользователь — активный организатор. Удалённые организации исключаем:
        их мероприятия и так отменены, в «Моих мероприятиях» не показываем."""
        stmt = (
            select(OrganizationOrganizer.organization_id)
            .join(
                Organization,
                Organization.id == OrganizationOrganizer.organization_id,
            )
            .where(
                OrganizationOrganizer.user_id == user_id,
                OrganizationOrganizer.is_active,
                Organization.is_active,
            )
            .order_by(OrganizationOrganizer.added_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        # dict.fromkeys — уникальные id с сохранением порядка добавления
        return list(dict.fromkeys(rows))
