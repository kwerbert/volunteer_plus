import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import update, func
from app.services.notification_service.db.models import Notification, NotificationToken

from app.services.notification_service.config import (
    NotificationType, Priority, PushStatus, settings
)
from app.services.notification_service.db.repository import NotificationRepository
from app.services.notification_service.providers.firebase_provider import FirebaseProvider
from app.services.notification_service.core.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Основной сервис уведомлений.
    Реализует fallback-стратегию: WebSocket → FCM Push.
    """

    def __init__(
            self,
            repository: NotificationRepository,
            firebase_provider: FirebaseProvider,
            ws_manager: WebSocketManager
    ):
        self.repo = repository
        self.firebase = firebase_provider
        self.ws_manager = ws_manager

    async def send_notification(
            self,
            user_id: int,
            title: str,
            body: str,
            notification_type: NotificationType,
            priority: Priority = Priority.NORMAL,
            data: Optional[dict] = None
    ) -> dict:
        """
        Отправка уведомления пользователю с fallback-стратегией.

        Логика:
        1. Создаём запись в БД
        2. Пробуем отправить через WebSocket (если пользователь онлайн)
        3. Если не доставлено или офлайн → отправляем FCM Push всем активным токенам
        4. Логируем результат
        """
        data = data or {}

        # 1. Создаём уведомление в БД
        notification = await self.repo.create_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            priority=priority,
            data=data
        )

        # 2. Формируем сообщение для клиента
        ws_message = {
            "type": "notification",
            "data": {
                "id": notification.id,
                "title": title,
                "body": body,
                "notification_type": notification_type.value,
                "priority": priority.value,
                "data": data,
                "sent_at": notification.sent_at.isoformat()
            }
        }

        # 3. Пробуем отправить через WebSocket
        ws_sent = 0
        if self.ws_manager.is_user_online(user_id):
            ws_sent = await self.ws_manager.send_to_user(ws_message, user_id)
            if ws_sent > 0:
                # Успешно доставлено через WebSocket
                await self.repo.session.execute(
                    update(Notification).where(Notification.id == notification.id).values(
                        delivered_at=func.now()
                    )
                )
                logger.info(f"Notification {notification.id} sent via WebSocket to user {user_id}")
                return {"success": True, "delivered_via": "websocket", "notification_id": notification.id}

        # 4. Fallback: отправка через FCM Push
        tokens = await self.repo.get_active_tokens(user_id)
        if not tokens:
            logger.warning(f"No active tokens for user {user_id}, push not sent")
            return {"success": False, "error": "NO_TOKENS", "notification_id": notification.id}

        push_results = []
        for token in tokens:
            result = await self.firebase.send_push_notification(
                device_token=token.device_token,
                title=title,
                body=body,
                data={**data, "notification_id": str(notification.id)},
                priority=priority.value.lower()
            )

            # Логируем результат
            status = PushStatus.SUCCESS if result["success"] else (
                PushStatus.UNREGISTERED if result.get("error") == "UNREGISTERED" else PushStatus.FAILED
            )
            await self.repo.create_push_log(
                notification_id=notification.id,
                device_token=token.device_token,
                status=status.value,
                error_message=result.get("message") if not result["success"] else None
            )

            # Если токен недействителен — деактивируем его
            if result.get("error") == "UNREGISTERED":
                await self.repo.session.execute(
                    update(NotificationToken).where(
                        NotificationToken.device_token == token.device_token
                    ).values(is_active=False)
                )

            push_results.append(result)

        # Обновляем delivered_at если хотя бы один пуш ушёл успешно
        if any(r["success"] for r in push_results):
            await self.repo.session.execute(
                update(Notification).where(Notification.id == notification.id).values(
                    delivered_at=func.now()
                )
            )

        logger.info(f"Notification {notification.id} sent via FCM to user {user_id}: {push_results}")
        return {
            "success": any(r["success"] for r in push_results),
            "delivered_via": "fcm",
            "notification_id": notification.id,
            "push_results": push_results
        }

    async def register_token(self, user_id: int, device_token: str, platform: str,
                             app_version: Optional[str] = None) -> dict:
        """Регистрация нового push-токена"""
        # Валидация токена (опционально, можно включить в продакшене)
        # is_valid = await self.firebase.validate_token(device_token)
        # if not is_valid:
        #     return {"success": False, "error": "INVALID_TOKEN"}

        token = await self.repo.create_token(
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            app_version=app_version
        )
        return {"success": True, "token_id": token.id}

    async def unregister_token(self, device_token: str) -> bool:
        """Удаление токена (при логауте)"""
        return await self.repo.delete_token(device_token)