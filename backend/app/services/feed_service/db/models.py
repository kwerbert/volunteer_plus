from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FeedServiceLog(Base):
    __tablename__ = "feed_service_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    request_id = Column(String(100), index=True)
    processing_time_ms = Column(Integer)
    event_count = Column(Integer, default=0)
    cache_hit = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class FeedEventCache(Base):
    __tablename__ = "feed_event_cache"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    cached_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)