"""Pydantic v2 схемы для Chat Service"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from enum import Enum
from datetime import datetime, timezone

class ChatTypeEnum(str, Enum):
    """Типы чатов"""
    EVENT = "event"  # Групповой чат мероприятия
    ORGANIZER = "organizer"  # Личный чат с организатором/представителем организации

class MessageTypeEnum(str, Enum):
    """Типы сообщений"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"

# === Request Schemas ===
class ChatCreateRequest(BaseModel):
    """Запрос создания чата"""
    chat_type: ChatTypeEnum
    participant_ids: List[int] = Field(..., min_length=1)
    title: Optional[str] = Field(None, max_length=255)
    event_id: Optional[int] = None
    organization_id: Optional[int] = None
    model_config = ConfigDict(json_schema_extra={"example": {
        "chat_type": "organizer",
        "participant_ids": [2],
        "title": None
    }})

class MessageCreateRequest(BaseModel):
    """Запрос отправки сообщения"""
    content: str = Field(..., min_length=1, max_length=4096)
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT
    attachment_url: Optional[str] = Field(None, max_length=512)
    model_config = ConfigDict(json_schema_extra={"example": {
        "content": "Привет! Готов помочь с мероприятием?",
        "message_type": "text",
        "attachment_url": None
    }})

class MarkReadRequest(BaseModel):
    """Запрос отметки прочтения"""
    message_ids: Optional[List[int]] = None

# === Response Schemas ===
class ChatMemberResponse(BaseModel):
    """Данные участника чата"""
    user_id: int
    role: str
    joined_at: datetime
    is_muted: bool
    model_config = ConfigDict(from_attributes=True)

class ChatResponse(BaseModel):
    """Данные чата"""
    id: int
    chat_type: ChatTypeEnum
    title: Optional[str] = None
    event_id: Optional[int] = None
    organization_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message: Optional[str] = None
    unread_count: int = 0
    members: List[ChatMemberResponse] = []
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    """Данные сообщения"""
    id: int
    chat_id: int
    sender_id: int
    content: str
    message_type: MessageTypeEnum
    attachment_url: Optional[str] = None
    is_read: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class MessagesListResponse(BaseModel):
    """Список сообщений с пагинацией"""
    messages: List[MessageResponse]
    total: int
    has_more: bool
    next_offset: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class ChatListResponse(BaseModel):
    """Список чатов пользователя"""
    chats: List[ChatResponse]
    total: int
    has_more: bool
    model_config = ConfigDict(from_attributes=True)

# === Service-to-Service Schemas ===
class UserVerifyResponse(BaseModel):
    user_id: int
    exists: bool
    is_active: bool
    full_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class OrganizationVerifyResponse(BaseModel):
    organization_id: int
    exists: bool
    name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class EventVerifyResponse(BaseModel):
    event_id: int
    exists: bool
    title: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class NotificationRequest(BaseModel):
    """Запрос отправки уведомления (в Notification Service)"""
    user_id: int
    title: str
    body: str
    data: Optional[dict] = None
    priority: str = "normal"
    model_config = ConfigDict(from_attributes=True)

# === Error Schema ===
class ErrorResponse(BaseModel):
    """Стандартный ответ об ошибке"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(from_attributes=True)