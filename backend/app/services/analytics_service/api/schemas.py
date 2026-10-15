# app/services/analytics_service/api/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserStatsBase(BaseModel):
    user_id: int
    total_hours: float = 0.0
    total_events: int = 0
    organizations_count: int = 0

class UserStatsResponse(UserStatsBase):
    id: int
    last_activity: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class OrganizationStats(BaseModel):
    organization_id: int
    organization_name: Optional[str] = None
    hours_worked: float
    events_completed: int
    role: Optional[str] = None

class OrganizationStatsResponse(BaseModel):
    user_id: int
    organizations: List[OrganizationStats]
    total_organizations: int
    generated_at: datetime = Field(default_factory=datetime.now)

class MonthlyStat(BaseModel):
    year: int
    month: int
    hours_worked: float
    events_completed: int

class MonthlyStatsResponse(BaseModel):
    user_id: int
    months: List[MonthlyStat]
    total_hours: float
    total_events: int
    generated_at: datetime = Field(default_factory=datetime.now)

class EventCompleteRequest(BaseModel):
    user_id: int
    hours_worked: Optional[float] = None
    role: Optional[str] = None

class EventCompleteResponse(BaseModel):
    success: bool
    user_id: int
    event_id: int
    hours_added: float
    message: str

class PreferredRoleResponse(BaseModel):
    role: str
    score: float
    events_count: int
    percentage: float

class PreferredRolesResponse(BaseModel):
    user_id: int
    roles: List[PreferredRoleResponse]
    primary_role: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)