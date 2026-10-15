from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class EventCreate(BaseModel):
    org_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    max_participants: int = Field(default=100, gt=0)


class EventResponse(BaseModel):
    id: int
    org_id: int
    title: str
    description: Optional[str]
    start_date: datetime
    location: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    user_id: int
    role_id: Optional[int] = None


class CheckInRequest(BaseModel):
    user_id: int
    qr_code: str


class ParticipationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: str
    model_config = ConfigDict(from_attributes=True)