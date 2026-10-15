from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from .db.models import Organization
from .schemas import OrganizationCreate


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: OrganizationCreate) -> Organization:
        existing = await self.db.execute(
            select(Organization).where(Organization.name == data.name)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Organization with this name already exists")

        new_org = Organization(
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            is_verified=False,
            rating=0.0,
            is_active=True
        )
        self.db.add(new_org)
        await self.db.commit()
        await self.db.refresh(new_org)
        return new_org

    async def get_list(
            self,
            category_id: Optional[int] = None,
            verified: Optional[bool] = None
    ) -> List[Organization]:
        query = select(Organization)
        if category_id is not None:
            query = query.where(Organization.category_id == category_id)
        if verified is not None:
            query = query.where(Organization.is_verified == verified)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, org_id: int) -> Optional[Organization]:
        return await self.db.get(Organization, org_id)

    async def verify_organization(self, org_id: int, verified: bool) -> Organization:
        org = await self.db.get(Organization, org_id)
        if not org:
            raise ValueError("Organization not found")

        org.is_verified = verified
        if verified:
            org.rating = min(org.rating + 1.0, 5.0)

        await self.db.commit()
        await self.db.refresh(org)
        return org