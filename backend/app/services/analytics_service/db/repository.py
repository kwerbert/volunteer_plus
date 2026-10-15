from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from .models import VolunteerStats, MonthlyStats, PreferredRole


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_stats(self, user_id: int) -> Optional[VolunteerStats]:
        stmt = select(VolunteerStats).where(VolunteerStats.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_or_update_stats(
            self,
            user_id: int,
            hours: float = 0.0,
            events: int = 0,
            org_id: Optional[int] = None,
            role: Optional[str] = None
    ) -> VolunteerStats:
        if org_id is not None:
            stmt = select(VolunteerStats).where(
                VolunteerStats.user_id == user_id,
                VolunteerStats.organization_id == org_id,
                VolunteerStats.role == role
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.hours_worked += hours
                existing.events_completed += events
                existing.last_activity = datetime.now(timezone.utc)
            else:
                new_stats = VolunteerStats(
                    user_id=user_id,
                    organization_id=org_id,
                    role=role,
                    hours_worked=hours,
                    events_completed=events,
                    last_activity=datetime.now(timezone.utc)
                )
                self.session.add(new_stats)
                existing = new_stats
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            # Если нет org_id – ничего не делаем или возвращаем заглушку
            # Но по логике этот кейс не должен вызываться. Возвращаем пустой объект с user_id.
            dummy = VolunteerStats(user_id=user_id, hours_worked=0, events_completed=0)
            return dummy

    async def get_stats_by_organization(self, user_id: int) -> List[Dict[str, Any]]:
        stmt = select(
            VolunteerStats.organization_id,
            func.sum(VolunteerStats.hours_worked).label('total_hours'),
            func.sum(VolunteerStats.events_completed).label('total_events'),
            VolunteerStats.role
        ).where(
            VolunteerStats.user_id == user_id,
            VolunteerStats.organization_id != None
        ).group_by(
            VolunteerStats.organization_id,
            VolunteerStats.role
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        return [
            {
                "organization_id": row.organization_id,
                "hours_worked": row.total_hours or 0.0,
                "events_completed": row.total_events or 0,
                "role": row.role
            }
            for row in rows
        ]

    async def get_monthly_stats(self, user_id: int, months: int = 12) -> List[MonthlyStats]:
        stmt = select(MonthlyStats).where(
            MonthlyStats.user_id == user_id
        ).order_by(
            MonthlyStats.year.desc(),
            MonthlyStats.month.desc()
        ).limit(months)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_monthly_stats(
            self,
            user_id: int,
            year: int,
            month: int,
            hours: float = 0.0,
            events: int = 0
    ) -> MonthlyStats:
        existing = await self.session.execute(
            select(MonthlyStats).where(
                and_(
                    MonthlyStats.user_id == user_id,
                    MonthlyStats.year == year,
                    MonthlyStats.month == month
                )
            )
        )
        existing_stats = existing.scalar_one_or_none()
        if existing_stats:
            existing_stats.hours_worked += hours
            existing_stats.events_completed += events
        else:
            new_stats = MonthlyStats(
                user_id=user_id,
                year=year,
                month=month,
                hours_worked=hours,
                events_completed=events
            )
            self.session.add(new_stats)
            existing_stats = new_stats

        await self.session.commit()
        await self.session.refresh(existing_stats)
        return existing_stats

    async def get_preferred_roles(self, user_id: int) -> List[PreferredRole]:
        stmt = select(PreferredRole).where(
            PreferredRole.user_id == user_id
        ).order_by(PreferredRole.score.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_preferred_roles(
            self,
            user_id: int,
            role: str,
            hours: float,
            events_count: int = 1
    ) -> PreferredRole:
        existing = await self.session.execute(
            select(PreferredRole).where(
                and_(
                    PreferredRole.user_id == user_id,
                    PreferredRole.role == role
                )
            )
        )
        existing_role = existing.scalar_one_or_none()
        if existing_role:
            existing_role.score += hours
            existing_role.events_count += events_count
        else:
            new_role = PreferredRole(
                user_id=user_id,
                role=role,
                score=hours,
                events_count=events_count
            )
            self.session.add(new_role)
            existing_role = new_role

        await self.session.commit()
        await self.session.refresh(existing_role)
        return existing_role