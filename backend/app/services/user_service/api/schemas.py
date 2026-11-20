from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRoleEnum(str, Enum):
    VOLUNTEER = "volunteer"
    ORGANIZER = "organizer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class LocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)


class UserSettingsUpdateRequest(BaseModel):
    search_radius_km: Optional[int] = Field(None, ge=1, le=100)
    show_only_subscriptions: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    language: Optional[str] = Field(None, pattern="^(ru)$")
    theme: Optional[str] = Field(None, pattern="^(light)$")
    main_organization_id: Optional[int] = Field(None, ge=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRoleEnum
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LocationResponse(BaseModel):
    id: int
    user_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserSettingsResponse(BaseModel):
    id: int
    user_id: int
    search_radius_km: int = 10
    show_only_subscriptions: bool = False
    notifications_enabled: bool = True
    language: str = "ru"
    theme: str = "light"
    updated_at: Optional[datetime] = None
    main_organization_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserVerifyResponse(BaseModel):
    user_id: int
    exists: bool
    is_active: bool
    role: Optional[UserRoleEnum] = None
    is_admin: bool = False
    model_config = ConfigDict(from_attributes=True)


class UserInternalResponse(BaseModel):
    """Данные пользователя для внутренних сервисов (поиск по email, этап 2)."""

    id: int
    email: str
    full_name: Optional[str] = None
    role: UserRoleEnum
    is_active: bool
    is_admin: bool
    model_config = ConfigDict(from_attributes=True)


class UserProfileForFeedResponse(BaseModel):
    id: int
    email: str
    role: UserRoleEnum
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    settings: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# === Organizer Applications ===


class OrganizerApplicationStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrganizerApplicationReviewRequest(BaseModel):
    """Решение админа. status — только approved/rejected."""

    status: Literal[
        OrganizerApplicationStatusEnum.APPROVED,
        OrganizerApplicationStatusEnum.REJECTED,
    ]
    rejection_reason: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class OrganizerApplicationResponse(BaseModel):
    id: int
    user_id: int
    status: OrganizerApplicationStatusEnum
    created_at: datetime
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizerApplicationCooldownError(BaseModel):
    """Тело detail для 429 (документация клиента)."""

    message: str
    rejected_at: datetime
    retry_at: datetime
    retry_after_seconds: int
