"""Общие enum'ы для системы уведомлений.

Используются notification_service (валидация/хранение) и chat_service
(формирование запросов), а также любыми другими сервисами, которые будут
слать уведомления. Единый источник правды исключает рассинхрон значений
между сервисами: если завтра кто-то переименует `CHAT` → `MESSAGE`,
это сломается на этапе сериализации в одном месте, а не в рантайме при
получении 422 от notification_service.
"""
from enum import Enum

class Platform(str, Enum):
    ANDROID = "ANDROID"
    IOS = "IOS"
    WEB = "WEB"


class NotificationType(str, Enum):
    CHAT = "CHAT"
    NEW_EVENT = "NEW_EVENT"
    EVENT_REMINDER = "EVENT_REMINDER"
    SYSTEM = "SYSTEM"


class Priority(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class PushStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNREGISTERED = "UNREGISTERED"