from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from app.services.notification_service.config import Platform, NotificationType, Priority, PushStatus

Base = declarative_base()


class NotificationToken(Base):
    """Push-токены устройств пользователей"""
    __tablename__ = "notification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True) #было user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_token = Column(String(255), unique=True, nullable=False, index=True)
    platform = Column(SQLEnum(Platform), default=Platform.ANDROID)
    app_version = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    notifications = relationship("Notification", back_populates="token", lazy="select")


class Notification(Base):
    """История уведомлений"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True) #было user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(String, nullable=False)
    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    priority = Column(SQLEnum(Priority), default=Priority.NORMAL)
    data = Column(JSON, default=dict)  # chat_id, event_id и т.д.
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    token = relationship("NotificationToken", back_populates="notifications", lazy="select")
    push_logs = relationship("PushLog", back_populates="notification", lazy="select", cascade="all, delete-orphan")


class PushLog(Base):
    """Лог отправки push-уведомлений (для отладки)"""
    __tablename__ = "push_logs"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    device_token = Column(String(255), nullable=False)
    status = Column(SQLEnum(PushStatus), nullable=False)
    error_message = Column(String, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notification = relationship("Notification", back_populates="push_logs", lazy="select")