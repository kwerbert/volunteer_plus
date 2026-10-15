from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List

from app.services.notification_service.config import Platform, NotificationType, Priority


# === Request Schemas ===

class CreateNotificationRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    notification_type: NotificationType
    priority: Priority = Priority.NORMAL
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RegisterTokenRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    device_token: str = Field(..., min_length=10)
    platform: Platform = Platform.ANDROID
    app_version: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# === Response Schemas ===

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    notification_type: str
    priority: str
    data: Dict[str, Any]
    is_read: bool
    sent_at: datetime
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class NotificationsListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)


class RegisterTokenResponse(BaseModel):
    success: bool
    token_id: Optional[int] = None
    error: Optional[str] = None


class SendNotificationResponse(BaseModel):
    success: bool
    delivered_via: Optional[str] = None
    notification_id: int
    error: Optional[str] = None
    push_results: Optional[List[Dict[str, Any]]] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


# === WebSocket Schemas ===

class WebSocketNotificationMessage(BaseModel):
    type: str = "notification"
    data: Dict[str, Any]

    model_config = ConfigDict(extra="allow")


class WebSocketHeartbeatMessage(BaseModel):
    type: str = "heartbeat"
    timestamp: float