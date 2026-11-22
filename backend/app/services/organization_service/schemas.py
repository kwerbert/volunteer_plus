from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None


class OrganizationCreate(OrganizationBase):
    # owner_user_id больше не принимается из тела: владелец = создатель из JWT.
    pass


class OrganizationResponse(OrganizationBase):
    id: int
    is_verified: bool = False
    rating: float = 0.0
    is_active: bool = True
    owner_user_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrganizationVerify(BaseModel):
    verified: bool


class OrgOrganizerRoleEnum(str, Enum):
    OWNER = "owner"
    ORGANIZER = "organizer"


class OrganizerAddRequest(BaseModel):
    email: EmailStr


class OrganizationOrganizerResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role_in_org: OrgOrganizerRoleEnum
    added_by: Optional[int] = None
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CurrentUser(BaseModel):
    """Снимок пользователя из user_service: свежие role/is_admin, не из JWT."""

    id: int
    role: str  # "volunteer" | "organizer"
    is_admin: bool = False
    is_active: bool = True
