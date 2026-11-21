import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ParticipationStatus(str, enum.Enum):
    REGISTERED = "registered"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"


class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    location = Column(String(255), nullable=True)
    max_participants = Column(Integer, default=100)
    qr_secret = Column(String(64), nullable=True)
    qr_check_enabled = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default=EventStatus.ACTIVE.value, nullable=False)
    image_url = Column(String(512), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    has_custom_roles = Column(Boolean, default=False, nullable=False)


class EventRole(Base):
    """Роль волонтёра на мероприятии"""

    __tablename__ = "event_roles"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    hours_value = Column(Float, default=4.0, nullable=False)
    max_participants = Column(Integer, nullable=True)  # None = без лимита


class Participation(Base):
    __tablename__ = "participations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    role_id = Column(Integer, ForeignKey("event_roles.id"), nullable=True)
    status = Column(
        SQLEnum(ParticipationStatus), default=ParticipationStatus.REGISTERED
    )
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    checked_in_at = Column(DateTime, nullable=True)
