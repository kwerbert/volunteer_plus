from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventStatusEnum(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


# === Роли мероприятия ===
class EventRoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    hours_value: float = Field(default=4.0, gt=0)
    max_participants: Optional[int] = Field(default=None, gt=0)


class EventRoleResponse(BaseModel):
    id: int
    event_id: int
    name: str
    description: Optional[str] = None
    hours_value: float
    max_participants: Optional[int] = None
    registered_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    org_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: int = Field(default=100, gt=0)
    roles: Optional[List[EventRoleCreate]] = None
    qr_check_enabled: bool = True
    image_url: Optional[str] = Field(default=None, max_length=512)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: Optional[int] = Field(default=None, gt=0)
    image_url: Optional[str] = Field(default=None, max_length=512)
    qr_check_enabled: Optional[bool] = None


class EventResponse(BaseModel):
    id: int
    org_id: int
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: Optional[int] = None
    qr_check_enabled: bool = True
    status: str = "active"
    image_url: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    has_custom_roles: bool = False
    roles: List[EventRoleResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    user_id: int
    event_role_id: Optional[int] = None
    role_id: Optional[int] = None

    @model_validator(mode="after")
    def _sync_role_fields(self):
        if (
            self.event_role_id is not None
            and self.role_id is not None
            and self.event_role_id != self.role_id
        ):
            raise ValueError("event_role_id и role_id не совпадают")
        if self.event_role_id is None:
            self.event_role_id = self.role_id
        if self.role_id is None:
            self.role_id = self.event_role_id
        return self


class UnregisterRequest(BaseModel):
    user_id: int


class CheckInRequest(BaseModel):
    user_id: int
    qr_code: Optional[str] = None


class ParticipationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: str
    role_id: Optional[int] = None
    registered_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# === Жизненный цикл ===
class EventCancelResponse(BaseModel):
    """4.2: мягкая отмена."""

    id: int
    status: str = "cancelled"
    cancelled_at: datetime
    cancelled_participations: int = 0
    notified_volunteers: int = 0


class EventCleanupResponse(BaseModel):
    """4.3: физическое удаление отменённых старше N дней."""

    deleted_events: int
    deleted_participations: int
    deleted_roles: int
    retention_days: int
    cutoff: datetime


class EventCompletionResponse(BaseModel):
    """4.4: перевод прошедших мероприятий в completed."""

    completed_events: int


class OrganizationEventsCancelResponse(BaseModel):
    """4.6: внутренний вызов при удалении организации."""

    organization_id: int
    cancelled_events: int
    cancelled_participations: int
    notified_volunteers: int
    completed_events: int = 0


class ParticipationRoleInfoResponse(BaseModel):
    event_id: int
    user_id: int
    status: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    hours_value: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
