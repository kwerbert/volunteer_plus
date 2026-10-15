from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime

from app.services.notification_service.db.models import NotificationToken, Notification, PushLog
from app.services.notification_service.config import NotificationType, Priority


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # === NotificationToken ===

    async def get_token(self, device_token: str) -> Optional[NotificationToken]:
        result = await self.session.execute(
            select(NotificationToken).where(NotificationToken.device_token == device_token)
        )
        return result.scalar_one_or_none()

    async def get_active_tokens(self, user_id: int) -> List[NotificationToken]:
        result = await self.session.execute(
            select(NotificationToken).where(
                NotificationToken.user_id == user_id,
                NotificationToken.is_active == True
            )
        )
        return result.scalars().all()

    async def create_token(self, user_id: int, device_token: str, platform: str,
                           app_version: Optional[str] = None) -> NotificationToken:
        # Деактивируем все токены с таким же device_token (любой user_id)
        await self.session.execute(
            update(NotificationToken).where(
                NotificationToken.device_token == device_token
            ).values(is_active=False)
        )

        # Создаём новый активный токен для текущего пользователя
        token = NotificationToken(
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            app_version=app_version,
            is_active=True
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def delete_token(self, device_token: str) -> bool:
        result = await self.session.execute(
            delete(NotificationToken).where(NotificationToken.device_token == device_token)
        )
        return result.rowcount > 0

    # === Notification ===

    async def create_notification(
            self,
            user_id: int,
            title: str,
            body: str,
            notification_type: NotificationType,
            priority: Priority,
            data: dict
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            priority=priority,
            data=data
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_notifications(
            self,
            user_id: int,
            page: int = 1,
            page_size: int = 20,
            is_read: Optional[bool] = None,
            notification_type: Optional[NotificationType] = None
    ) -> tuple[List[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)

        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        if notification_type:
            query = query.where(Notification.notification_type == notification_type)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        # Paginate
        query = query.order_by(Notification.sent_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def mark_as_read(self, notification_id: int) -> bool:
        result = await self.session.execute(
            update(Notification).where(Notification.id == notification_id).values(
                is_read=True,
                read_at=func.now()
            )
        )
        return result.rowcount > 0

    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            delete(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        return result.rowcount > 0

    async def get_notification(self, notification_id: int) -> Optional[Notification]:
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    # === PushLog ===

    async def create_push_log(
            self,
            notification_id: int,
            device_token: str,
            status: str,
            error_message: Optional[str] = None
    ) -> PushLog:
        log = PushLog(
            notification_id=notification_id,
            device_token=device_token,
            status=status,
            error_message=error_message
        )
        self.session.add(log)
        await self.session.flush()
        return log