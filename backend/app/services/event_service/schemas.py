from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# === Роли мероприятия (этап 3) ===
class EventRoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    hours_value: float = Field(default=4.0, gt=0)
    max_participants: Optional[int] = Field(default=None, gt=0)  # None = без лимита


class EventRoleResponse(BaseModel):
    id: int
    event_id: int
    name: str
    description: Optional[str] = None
    hours_value: float
    max_participants: Optional[int] = None
    registered_count: int = 0  # этап 3.7
    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    org_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: int = Field(default=100, gt=0)
    # === Этап 3.3 ===
    roles: Optional[List[EventRoleCreate]] = None
    qr_check_enabled: bool = True
    image_url: Optional[str] = Field(default=None, max_length=512)


class EventUpdate(BaseModel):
    """Редактирование мероприятия (этап 3.1). Роли не меняются после создания —
    к ним уже привязаны регистрации."""

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
    # === Этап 3 (все новые поля с дефолтами — обратная совместимость) ===
    qr_check_enabled: bool = True
    status: str = "active"
    image_url: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    has_custom_roles: bool = False
    roles: List[EventRoleResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    user_id: int
    role_id: Optional[int] = None  # этап 3.5: id из event_roles


class CheckInRequest(BaseModel):
    user_id: int
    qr_code: Optional[str] = None  # не обязателен, если qr_check_enabled=False


class ParticipationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: str
    role_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
