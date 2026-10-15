from abc import ABC, abstractmethod
from typing import Dict, Any


class PushProvider(ABC):
    """Абстрактный интерфейс для push-провайдеров"""

    @abstractmethod
    async def send_push_notification(
            self,
            device_token: str,
            title: str,
            body: str,
            data: Dict[str, str],
            priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Отправка push-уведомления

        Args:
            device_token: Токен устройства
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные (только строки!)
            priority: "high" или "normal"

        Returns:
            Dict с результатом: {"success": bool, "message_id": str, "error": str}
        """
        pass

    @abstractmethod
    async def validate_token(self, device_token: str) -> bool:
        """Проверка валидности токена (опционально)"""
        pass