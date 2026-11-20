import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    description = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    # Дублирует владельца для быстрого доступа (chat_service читает это поле).
    # Источник правды — organization_organizers c role_in_org='owner'.
    owner_user_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)


class OrgOrganizerRole(str, enum.Enum):
    OWNER = "owner"
    ORGANIZER = "organizer"


class OrganizationOrganizer(Base):
    """Связь «организация ↔ организаторы» (этап 2).

    Владелец — не роль пользователя, а запись здесь с role_in_org='owner'.
    Удаление мягкое (is_active=False), слоты освобождаются partial-индексами.
    """

    __tablename__ = "organization_organizers"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id = Column(Integer, nullable=False, index=True)
    role_in_org = Column(
        SQLEnum(
            OrgOrganizerRole,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],  # в БД: owner/organizer
        ),
        default=OrgOrganizerRole.ORGANIZER,
        nullable=False,
    )
    added_by = Column(Integer, nullable=True)  # кто добавил (аудит)
    added_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        # Не больше одного активного членства (org, user) — на уровне БД,
        # гонка двух параллельных POST не создаст дубликат.
        Index(
            "uq_organization_organizers_active",
            "organization_id",
            "user_id",
            unique=True,
            sqlite_where=text("is_active = 1"),
        ),
        # Один аккаунт — максимум одна СВОЯ организация (активное владение).
        Index(
            "uq_organization_organizers_one_owner",
            "user_id",
            unique=True,
            sqlite_where=text("role_in_org = 'owner' AND is_active = 1"),
        ),
    )
