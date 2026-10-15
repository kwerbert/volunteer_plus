from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class SubscriptionBase(BaseModel):
    user_id: int
    org_id: int
    role: Optional[str] = "volunteer"

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    role: Optional[str] = None
    active: Optional[bool] = None

class SubscriptionResponse(SubscriptionBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SubscriptionCheckResponse(BaseModel):
    is_subscribed: bool
    subscription_id: Optional[int] = None
    active: bool = False
    role: Optional[str] = None

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None