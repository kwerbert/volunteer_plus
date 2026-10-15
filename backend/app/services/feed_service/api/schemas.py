"""
Pydantic схемы для валидации запросов и ответов
Обновлено для Pydantic v2: model_config вместо class Config
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class FeedSectionType(str, Enum):
    FROM_SUBSCRIPTIONS = "from_subscriptions"
    ORGANIZATION_OF_THE_DAY = "organization_of_the_day"
    RECOMMENDATIONS = "recommendations"



class FeedFilterParams(BaseModel):
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lon: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[int] = Field(None, ge=1, le=100)
    category_ids: Optional[List[int]] = None # было category_ids: Optional[List[int]] = Field(default_factory=list)
    role_ids: Optional[List[int]] = None # было role_ids: Optional[List[int]] = Field(default_factory=list)
    date_from: Optional[datetime] = Field(None)
    date_to: Optional[datetime] = Field(None)
    show_only_subscriptions: Optional[bool] = Field(False)
    page: Optional[int] = Field(1, ge=1)
    page_size: Optional[int] = Field(20, ge=1, le=50)

    model_config = ConfigDict(from_attributes=True)

class OrganizationPreview(BaseModel):
    id: int
    name: str
    logo_url: Optional[str] = None
    rating: float = 0.0
    verified: bool = False
    category_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class EventPreview(BaseModel):
    """
    Критически важно: все поля должны совпадать с Android FeedResponse.kt
    """
    id: int
    title: str
    organization: OrganizationPreview
    description_preview: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    distance_km: Optional[float] = None
    required_role_id: Optional[int] = None
    max_participants: Optional[int] = None
    registered_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class FeedSection(BaseModel):
    section_type: FeedSectionType
    section_title: str
    events: List[EventPreview]
    layout: str = Field("horizontal", description="horizontal или vertical")

    model_config = ConfigDict(from_attributes=True)

class FeedResponse(BaseModel):
    user_id: int
    generated_at: datetime
    filters_applied: Dict[str, Any]
    sections: List[FeedSection]
    total_events: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)