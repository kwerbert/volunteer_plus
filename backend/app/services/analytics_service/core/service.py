import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp

from app.services.analytics_service.api.schemas import (
    EventCompleteResponse,
    MonthlyStatsResponse,
    OrganizationStatsResponse,
    PreferredRoleResponse,
    PreferredRolesResponse,
    UserStatsResponse,
)
from app.services.analytics_service.config import settings
from app.services.analytics_service.db.repository import AnalyticsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self.repo = repo
        self.settings = settings

    async def get_user_analytics(self, user_id: int) -> UserStatsResponse:
        try:
            # 1. Получаем агрегированную статистику по всем организациям
            org_stats = await self.repo.get_stats_by_organization(user_id)

            # Суммируем часы и мероприятия по ВСЕМ организациям
            total_hours = sum(org.get("hours_worked", 0.0) for org in org_stats)
            total_events = sum(org.get("events_completed", 0) for org in org_stats)

            # 2. Достаем базовую запись для метаданных (id, created_at)
            stats = await self.repo.get_user_stats(user_id)
            if not stats:
                # Если нет вообще никаких записей (новый пользователь)
                return UserStatsResponse(
                    id=0,
                    user_id=user_id,
                    total_hours=0.0,
                    total_events=0,
                    organizations_count=0,
                    last_activity=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=None,
                )

            return UserStatsResponse(
                id=stats.id,
                user_id=user_id,
                total_hours=total_hours,
                total_events=total_events,
                organizations_count=len(org_stats),
                last_activity=stats.last_activity,
                created_at=stats.created_at,
                updated_at=stats.updated_at,
            )
        except Exception as e:
            logger.error(
                f"Error in get_user_analytics for user {user_id}: {e}", exc_info=True
            )
            raise

    async def get_organization_analytics(
        self, user_id: int
    ) -> OrganizationStatsResponse:
        org_data = await self.repo.get_stats_by_organization(user_id)
        organizations = []
        for org in org_data:
            org_name = org.get("organization_name_snapshot")
            if not org_name:
                org_name = await self._get_organization_name(org["organization_id"])
            organizations.append(
                {
                    "organization_id": org["organization_id"],
                    "organization_name": org_name,
                    "hours_worked": org["hours_worked"],
                    "events_completed": org["events_completed"],
                    "role": org["role"],
                }
            )
        return OrganizationStatsResponse(
            user_id=user_id,
            organizations=organizations,
            total_organizations=len(organizations),
            generated_at=datetime.now(),
        )

    async def get_monthly_analytics(
        self, user_id: int, months: int = 12
    ) -> MonthlyStatsResponse:
        """Ежемесячная аналитика"""
        monthly_data = await self.repo.get_monthly_stats(user_id, months)
        months_list = [
            {
                "year": m.year,
                "month": m.month,
                "hours_worked": m.hours_worked,
                "events_completed": m.events_completed,
            }
            for m in monthly_data
        ]
        total_hours = sum(m.hours_worked for m in monthly_data)
        total_events = sum(m.events_completed for m in monthly_data)
        return MonthlyStatsResponse(
            user_id=user_id,
            months=months_list,
            total_hours=total_hours,
            total_events=total_events,
            generated_at=datetime.now(),
        )

    async def complete_event(
        self,
        event_id: int,
        user_id: int,
        hours: Optional[float] = None,
        role: Optional[str] = None,
    ) -> EventCompleteResponse:
        event_info = await self._get_event_info(event_id)
        if not event_info:
            return EventCompleteResponse(
                success=False,
                user_id=user_id,
                event_id=event_id,
                hours_added=0.0,
                message="Мероприятие не найдено",
            )

        # 8.1: event_role_id → hours_value; 8.2: event_roles.name
        participation = await self._get_participation_role_info(event_id, user_id)
        hours_worked = hours
        role_name = role
        if participation:
            if hours_worked is None:
                hours_worked = participation.get("hours_value")
            if role_name is None:
                role_name = participation.get("role_name")
        if hours_worked is None:
            hours_worked = self.settings.DEFAULT_EVENT_HOURS

        org_id = event_info.get("org_id")
        org_name = await self._get_organization_name(org_id) if org_id else None

        await self.repo.create_or_update_stats(
            user_id=user_id,
            hours=hours_worked,
            events=1,
            org_id=org_id,
            role=role_name,
            org_name=org_name,
        )

        # Обновляем месячную статистику
        now = datetime.now()
        await self.repo.create_monthly_stats(
            user_id=user_id,
            year=now.year,
            month=now.month,
            hours=hours_worked,
            events=1,
        )

        # 8.2: предпочтительные роли — по названию роли мероприятия
        if role_name:
            await self.repo.update_preferred_roles(
                user_id=user_id, role=role_name, hours=hours_worked, events_count=1
            )

        logger.info(
            "Event %s completed for user %s: +%s hours (role=%s)",
            event_id,
            user_id,
            hours_worked,
            role_name,
        )
        return EventCompleteResponse(
            success=True,
            user_id=user_id,
            event_id=event_id,
            hours_added=hours_worked,
            message=f"Добавлено {hours_worked} часов волонтёрства",
        )

    async def get_preferred_roles(self, user_id: int) -> PreferredRolesResponse:
        """Получение предпочтительных ролей пользователя"""
        roles = await self.repo.get_preferred_roles(user_id)
        if not roles:
            return PreferredRolesResponse(
                user_id=user_id,
                roles=[],
                primary_role=None,
                generated_at=datetime.now(),
            )
        total_score = sum(r.score for r in roles)
        roles_list = []
        for r in roles:
            percentage = (r.score / total_score * 100) if total_score > 0 else 0
            roles_list.append(
                PreferredRoleResponse(
                    role=r.role,
                    score=r.score,
                    events_count=r.events_count,
                    percentage=round(percentage, 2),
                )
            )
        primary_role = roles_list[0].role if roles_list else None
        return PreferredRolesResponse(
            user_id=user_id,
            roles=roles_list,
            primary_role=primary_role,
            generated_at=datetime.now(),
        )

    async def _get_organization_name(self, org_id: int) -> Optional[str]:
        """Получение названия организации из Organization Service.
        GET отдаёт и неактивные организации — имя доступно и после удаления."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.settings.ORGANIZATION_SERVICE_URL}/api/v1/organizations/{org_id}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("name")
        except Exception as e:
            logger.error(f"Error fetching organization {org_id}: {e}")
        return None

    async def _get_event_info(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о мероприятии из Event Service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.settings.EVENT_SERVICE_URL}/api/v1/events/{event_id}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
        return None

    async def _get_participation_role_info(
        self, event_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.settings.EVENT_SERVICE_URL}"
                    f"/internal/events/{event_id}/participations/{user_id}",
                    headers={"X-Service-Key": self.settings.SERVICE_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status != 404:
                        logger.warning(
                            "Event Service participation event=%s user=%s: HTTP %s",
                            event_id,
                            user_id,
                            response.status,
                        )
        except Exception as e:
            logger.error(
                f"Error fetching participation event={event_id} user={user_id}: {e}"
            )
        return None
