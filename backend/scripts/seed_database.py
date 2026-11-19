#!/usr/bin/env python3
"""
Наполнение баз данных тестовыми данными для демонстрации всех возможностей.
Запуск: python scripts/seed_database.py
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.services.analytics_service.db.models import (
    MonthlyStats,
    PreferredRole,
    VolunteerStats,
)
from app.services.chat_service.db.models import Chat, ChatMember, ChatTypeEnum, Message
from app.services.event_service.db.models import (
    Event,
    Participation,
    ParticipationStatus,
)

# --- Модели остальных сервисов (volunteer_plus.db) ---
from app.services.organization_service.db.models import Category, Organization
from app.services.subscription_service.db.models import Subscription

# --- Модели user_service (users.db) ---
from app.services.user_service.core.security import hash_password
from app.services.user_service.db.models import (
    OrganizerApplication,
    OrganizerApplicationStatus,
    User,
    UserRoleEnum,
    UserSettings,
)

VOLUNTEER_DB_URL = "sqlite+aiosqlite:///./volunteer_plus.db"
USER_DB_URL = "sqlite+aiosqlite:///./users.db"

volunteer_engine = create_async_engine(VOLUNTEER_DB_URL, echo=False)
user_engine = create_async_engine(USER_DB_URL, echo=False)

# ✅ У каждого движка — СВОЯ фабрика сессий (вот чего не хватало)
user_session_maker = async_sessionmaker(user_engine, expire_on_commit=False)
volunteer_session_maker = async_sessionmaker(volunteer_engine, expire_on_commit=False)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def get_user_session() -> AsyncGenerator[AsyncSession, None]:
    async with user_session_maker() as session:
        yield session


async def get_volunteer_session() -> AsyncGenerator[AsyncSession, None]:
    async with volunteer_session_maker() as session:
        yield session


async def seed_all() -> None:
    """Основная функция наполнения БД"""
    # 1. Таблицы users.db
    async with user_engine.begin() as conn:
        from app.services.user_service.db.models import Base as UserBase

        await conn.run_sync(UserBase.metadata.create_all)

    # 2. Таблицы volunteer_plus.db
    async with volunteer_engine.begin() as conn:
        from app.services.analytics_service.db.models import Base as AnalyticsBase
        from app.services.chat_service.db.models import Base as ChatBase
        from app.services.event_service.db.models import Base as EventBase
        from app.services.organization_service.db.models import Base as OrgBase
        from app.services.subscription_service.db.models import Base as SubBase

        for base in (OrgBase, EventBase, SubBase, ChatBase, AnalyticsBase):
            await conn.run_sync(base.metadata.create_all)

    # 3. Данные users.db
    async with user_session_maker() as session:
        await seed_users(session)
        await seed_organizer_applications(session)
        await session.commit()

    # 4. Данные volunteer_plus.db
    async with volunteer_session_maker() as session:
        await seed_categories(session)
        await seed_organizations(session)
        await seed_events(session)
        await seed_participations(session)
        await seed_subscriptions(session)
        await seed_chats(session)
        await seed_analytics(session)
        await session.commit()

    print("✅ Базы данных успешно наполнены тестовыми данными")


# ----- users.db -----


async def seed_users(session: AsyncSession) -> None:
    """Волонтёр, организатор, админ-волонтёр, организатор-владелец."""
    password_hash = hash_password("password123")

    specs = [
        # (id, email, full_name, role, is_admin)
        (1, "volunteer@example.com", "Иван Волонтёров", UserRoleEnum.VOLUNTEER, False),
        (
            2,
            "organizer@example.com",
            "Ольга Организаторова",
            UserRoleEnum.ORGANIZER,
            False,
        ),
        (3, "admin@example.com", "Админ Модераторов", UserRoleEnum.VOLUNTEER, True),
        (4, "owner@example.com", "Пётр Владелец", UserRoleEnum.ORGANIZER, False),
    ]

    for user_id, email, full_name, role, is_admin in specs:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            existing.role = role
            existing.is_admin = is_admin
            continue

        session.add(
            User(
                id=user_id,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                is_admin=is_admin,
                is_active=True,
                is_verified=True,
                created_at=now_utc(),
            )
        )
        session.add(UserSettings(user_id=user_id))

    await session.flush()


async def seed_organizer_applications(session: AsyncSession) -> None:
    """Одобренная заявка организатора + отклонённая заявка волонтёра."""
    now = now_utc()
    session.add_all(
        [
            OrganizerApplication(
                id=1,
                user_id=2,
                status=OrganizerApplicationStatus.APPROVED,
                created_at=now - timedelta(days=2),
                reviewed_by=3,
                reviewed_at=now - timedelta(days=2) + timedelta(hours=1),
            ),
            OrganizerApplication(
                id=2,
                user_id=1,
                status=OrganizerApplicationStatus.REJECTED,
                created_at=now - timedelta(days=1),
                reviewed_by=3,
                reviewed_at=now - timedelta(days=1),
                rejection_reason="Недостаточно информации о деятельности",
            ),
        ]
    )
    await session.flush()


# ----- volunteer_plus.db -----


async def seed_categories(session: AsyncSession) -> None:
    session.add_all(
        [
            Category(id=1, name="Экология"),
            Category(id=2, name="Образование"),
            Category(id=3, name="Социальная помощь"),
        ]
    )
    await session.flush()


async def seed_organizations(session: AsyncSession) -> None:
    session.add_all(
        [
            Organization(
                id=1,
                name="Зелёный город",
                description="Экологическая организация",
                is_verified=True,
                rating=4.8,
                category_id=1,
                owner_user_id=2,
                is_active=True,
                created_at=now_utc(),
            ),
            Organization(
                id=2,
                name="Помощь детям",
                description="Социальная помощь",
                is_verified=True,
                rating=4.5,
                category_id=3,
                owner_user_id=4,
                is_active=True,
                created_at=now_utc(),
            ),
        ]
    )
    await session.flush()


async def seed_events(session: AsyncSession) -> None:
    now = now_utc()
    session.add_all(
        [
            Event(
                id=1,
                org_id=1,
                title="Уборка парка",
                description="Субботник в центральном парке",
                start_date=now + timedelta(days=3),
                end_date=now + timedelta(days=3, hours=4),
                location="Центральный парк",
                max_participants=50,
                qr_secret="qr_secret_1",
            ),
            Event(
                id=2,
                org_id=1,
                title="Посадка деревьев",
                description="Высадка саженцев",
                start_date=now + timedelta(days=7),
                end_date=now + timedelta(days=7, hours=3),
                location="Парк Победы",
                max_participants=30,
                qr_secret="qr_secret_2",
            ),
            Event(
                id=3,
                org_id=2,
                title="Помощь в детском доме",
                description="Проведение мастер-классов",
                start_date=now + timedelta(days=5),
                end_date=now + timedelta(days=5, hours=5),
                location="Детский дом №1",
                max_participants=20,
                qr_secret="qr_secret_3",
            ),
        ]
    )
    await session.flush()


async def seed_participations(session: AsyncSession) -> None:
    # ✅ status — члены enum ParticipationStatus, а не строки "checked_in":
    # SQLEnum хранит ИМЕНА ("CHECKED_IN"), строка-значение упала бы с LookupError
    session.add_all(
        [
            Participation(
                event_id=1,
                user_id=1,
                status=ParticipationStatus.CHECKED_IN,
                registered_at=now_utc() - timedelta(days=2),
                checked_in_at=now_utc(),
            ),
            Participation(
                event_id=2,
                user_id=1,
                status=ParticipationStatus.REGISTERED,
                registered_at=now_utc() - timedelta(days=1),
            ),
            Participation(
                event_id=3,
                user_id=1,
                status=ParticipationStatus.REGISTERED,
                registered_at=now_utc() - timedelta(hours=12),
            ),
        ]
    )
    await session.flush()


async def seed_subscriptions(session: AsyncSession) -> None:
    session.add_all(
        [
            Subscription(
                user_id=1,
                org_id=1,
                role="volunteer",
                active=True,
                created_at=now_utc() - timedelta(days=30),
            ),
            Subscription(
                user_id=1,
                org_id=2,
                role="volunteer",
                active=True,
                created_at=now_utc() - timedelta(days=15),
            ),
        ]
    )
    await session.flush()


async def seed_chats(session: AsyncSession) -> None:
    session.add_all(
        [
            Chat(
                id=1,
                chat_type=ChatTypeEnum.ORGANIZER,
                organization_id=1,
                is_active=True,
                created_at=now_utc(),
            ),
            Chat(
                id=2,
                chat_type=ChatTypeEnum.EVENT,
                title="Чат: Уборка парка",
                event_id=1,
                organization_id=1,
                is_active=True,
                created_at=now_utc(),
            ),
            ChatMember(chat_id=1, user_id=1, role="member", joined_at=now_utc()),
            ChatMember(chat_id=1, user_id=2, role="admin", joined_at=now_utc()),
            ChatMember(chat_id=2, user_id=1, role="member", joined_at=now_utc()),
            ChatMember(chat_id=2, user_id=2, role="organizer", joined_at=now_utc()),
            Message(
                chat_id=1,
                sender_id=1,
                content="Привет! Как дела?",
                is_read=True,
                created_at=now_utc() - timedelta(hours=2),
            ),
            Message(
                chat_id=1,
                sender_id=2,
                content="Всё отлично, спасибо!",
                is_read=True,
                created_at=now_utc() - timedelta(hours=1),
            ),
            Message(
                chat_id=2,
                sender_id=2,
                content="Добро пожаловать в чат мероприятия!",
                is_read=False,
                created_at=now_utc() - timedelta(minutes=30),
            ),
        ]
    )
    await session.flush()


async def seed_analytics(session: AsyncSession) -> None:
    session.add_all(
        [
            VolunteerStats(
                user_id=1,
                organization_id=1,
                role="Участник",
                hours_worked=12.5,
                events_completed=3,
                last_activity=now_utc(),
            ),
            VolunteerStats(
                user_id=1,
                organization_id=2,
                role="Помощник",
                hours_worked=8.0,
                events_completed=2,
                last_activity=now_utc() - timedelta(days=5),
            ),
        ]
    )

    months = []
    base = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for i in range(6):
        month_date = base - timedelta(days=30 * i)
        hours = 8.0 * (6 - i)
        months.append(
            MonthlyStats(
                user_id=1,
                year=month_date.year,
                month=month_date.month,
                hours_worked=hours,
                events_completed=int(hours / 4),
            )
        )
    session.add_all(months)

    session.add_all(
        [
            PreferredRole(user_id=1, role="Участник", score=15.0, events_count=4),
            PreferredRole(user_id=1, role="Координатор", score=8.5, events_count=2),
        ]
    )
    await session.flush()


if __name__ == "__main__":
    asyncio.run(seed_all())
