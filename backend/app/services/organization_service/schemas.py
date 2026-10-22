from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None


class OrganizationCreate(OrganizationBase):
    owner_user_id: Optional[int] = None


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