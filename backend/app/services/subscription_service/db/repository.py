from datetime import datetime, timezone
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from .models import Subscription, SubscriptionLog


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user(self, user_id: int, active_only: bool = True) -> List[Subscription]:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        if active_only:
            stmt = stmt.where(Subscription.active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, sub_id: int) -> Optional[Subscription]:
        stmt = select(Subscription).where(Subscription.id == sub_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_org(self, user_id: int, org_id: int) -> Optional[Subscription]:
        stmt = select(Subscription).where(
            and_(Subscription.user_id == user_id, Subscription.org_id == org_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user_id: int, org_id: int, role: str = "volunteer") -> Subscription:
        new_sub = Subscription(user_id=user_id, org_id=org_id, role=role)
        self.session.add(new_sub)
        await self.session.commit()
        await self.session.refresh(new_sub)
        return new_sub

    async def soft_delete(self, sub_id: int) -> bool:
        stmt = update(Subscription).where(Subscription.id == sub_id).values(active=False)
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def update_role(self, sub_id: int, role: str, active: bool) -> Optional[Subscription]:
        stmt = update(Subscription).where(Subscription.id == sub_id).values(
            role=role, active=active, updated_at=datetime.now(timezone.utc)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(sub_id)

    async def log_action(
            self,
            user_id: int,
            org_id: int,
            action: str,
            sub_id: Optional[int] = None,
            details: Optional[str] = None
    ):
        log = SubscriptionLog(
            subscription_id=sub_id,
            user_id=user_id,
            org_id=org_id,
            action=action,
            details=details
        )
        self.session.add(log)
        await self.session.commit()