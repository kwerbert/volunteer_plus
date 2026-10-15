import asyncio
from typing import Dict, Any, Optional
from firebase_admin import credentials, messaging, initialize_app
from pathlib import Path

from app.services.notification_service.providers.push_provider import PushProvider
from app.services.notification_service.config import settings


class FirebaseProvider(PushProvider):
    _initialized = False

    def __init__(self, service_account_path: Optional[str]):
        self.service_account_path = service_account_path
        self.enabled = bool(service_account_path and Path(service_account_path).is_file())
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Инициализация Firebase Admin SDK (только один раз)"""
        if self.enabled and not FirebaseProvider._initialized:
            cred = credentials.Certificate(self.service_account_path)
            initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
            FirebaseProvider._initialized = True

    async def send_push_notification(
            self,
            device_token: str,
            title: str,
            body: str,
            data: Dict[str, str],
            priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Отправка push-уведомления через FCM
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "FCM_NOT_CONFIGURED",
                "message": "Set NOTIFICATION_FIREBASE_CREDENTIALS_PATH to enable push notifications"
            }

        try:
            # FCM принимает данные только как строки
            fcm_data = {k: str(v) for k, v in data.items()}

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=fcm_data,
                token=device_token,
                android=messaging.AndroidConfig(
                    priority="high" if priority == "high" else "normal",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="volunteer_notifications",  # нужно создать на клиенте
                        click_action="com.example.myapplication.NOTIFICATION_CLICK"
                    ),
                    ttl=f"{settings.PUSH_TTL_SECONDS}s"
                ),
                apns=messaging.APNSConfig(  # на будущее, если добавим iOS
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            content_available=True
                        )
                    )
                )
            )

            # Отправка (синхронный вызов, но можно обернуть в executor)
            loop = asyncio.get_event_loop()
            message_id = await loop.run_in_executor(
                None,
                lambda: messaging.send(message)
            )

            return {"success": True, "message_id": message_id}

        except messaging.UnregisteredError:
            # Токен недействителен (приложение удалено/сброшено)
            return {"success": False, "error": "UNREGISTERED", "message": "Token not registered"}
        except messaging.InvalidArgumentError as e:
            return {"success": False, "error": "INVALID_TOKEN", "message": str(e)}
        except Exception as e:
            # Логировать ошибку в продакшене!
            return {"success": False, "error": "SEND_FAILED", "message": str(e)}

    async def validate_token(self, device_token: str) -> bool:
        """
        Проверка токена через пробную отправку (дорого, использовать осторожно)
        """
        if not self.enabled:
            return False

        try:
            # Отправляем "тихое" тестовое сообщение
            message = messaging.Message(
                data={"test": "true"},
                token=device_token,
                android=messaging.AndroidConfig(priority="normal")
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: messaging.send(message))
            return True
        except messaging.UnregisteredError:
            return False
        except:
            return False  # При ошибках сети считаем токен валидным
