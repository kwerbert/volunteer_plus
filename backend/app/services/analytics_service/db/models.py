from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()

class VolunteerStats(Base):
    __tablename__ = "volunteer_stats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    role = Column(String(100), nullable=True)
    hours_worked = Column(Float, default=0.0)
    events_completed = Column(Integer, default=0)
    last_activity = Column(DateTime, nullable=True)
    # ИСПРАВЛЕНО: timezone-aware datetime
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

class MonthlyStats(Base):
    __tablename__ = "monthly_stats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    hours_worked = Column(Float, default=0.0)
    events_completed = Column(Integer, default=0)
    # ИСПРАВЛЕНО
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class PreferredRole(Base):
    __tablename__ = "preferred_roles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(100), nullable=False)
    score = Column(Float, default=0.0)
    events_count = Column(Integer, default=0)
    # ИСПРАВЛЕНО
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)