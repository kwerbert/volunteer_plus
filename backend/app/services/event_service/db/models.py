from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class ParticipationStatus(str, enum.Enum):
    REGISTERED = "registered"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"


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


class Participation(Base):
    __tablename__ = "participations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    role_id = Column(Integer, nullable=True)
    status = Column(SQLEnum(ParticipationStatus), default=ParticipationStatus.REGISTERED)
    registered_at = Column(DateTime, default=datetime.utcnow)
    checked_in_at = Column(DateTime, nullable=True)