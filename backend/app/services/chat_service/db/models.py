from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum as SQLEnum, ForeignKey, func, \
    JSON  # ✅ ДОБАВЛЕНО JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()


class ChatTypeEnum(str, enum.Enum):
    """Типы чатов"""
    # ❌ УДАЛЕНО: PERSONAL = "personal"
    ORGANIZER = "organizer"  # ✅ Личный чат с организатором
    EVENT = "event"  # ✅ Групповой чат мероприятия


class MessageTypeEnum(str, enum.Enum):
    """Типы сообщений"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


class Chat(Base):
    """Модель чата"""
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    chat_type = Column(SQLEnum(ChatTypeEnum, native_enum=False), nullable=False)
    title = Column(String(255), nullable=True)
    event_id = Column(Integer, nullable=True)
    organization_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    scheduled_delete_at = Column(DateTime, nullable=True)
    deletion_config = Column(JSON, nullable=True)  # ✅ ТЕПЕРЬ РАБОТАЕТ

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")


class ChatMember(Base):
    """Участники чата"""
    __tablename__ = "chat_members"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    role = Column(String(50), default="member", nullable=False)  # member, admin, organizer
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    left_at = Column(DateTime, nullable=True)
    is_muted = Column(Boolean, default=False, nullable=False)

    chat = relationship("Chat", back_populates="members")

    __table_args__ = (
        # Уникальная комбинация chat_id + user_id для предотвращения дубликатов
        # (но разрешаем несколько записей если пользователь покинул и вернулся)
    )


class Message(Base):
    """Сообщения в чате"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageTypeEnum, native_enum=False), default=MessageTypeEnum.TEXT, nullable=False)
    attachment_url = Column(String(512), nullable=True)  # Для image/file
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    chat = relationship("Chat", back_populates="messages")