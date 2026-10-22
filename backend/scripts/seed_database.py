#!/usr/bin/env python3
"""
Наполнение баз данных тестовыми данными для демонстрации всех возможностей.
Запуск: python scripts/seed_database.py
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Импорты моделей всех сервисов
from typing import AsyncGenerator
from app.services.user_service.db.models import Base as UserBase, User, UserSettings, UserLocation, RefreshToken, UserRoleEnum
from app.services.organization_service.db.models import Base as OrgBase, Organization, Category
from app.services.event_service.db.models import Base as EventBase, Event, Participation, ParticipationStatus
from app.services.subscription_service.db.models import Base as SubBase, Subscription, SubscriptionLog
from app.services.chat_service.db.models import Base as ChatBase, Chat, ChatMember, Message, ChatTypeEnum, MessageTypeEnum
from app.services.analytics_service.db.models import Base as AnalyticsBase, VolunteerStats, MonthlyStats, PreferredRole
from app.services.user_service.core.security import hash_password

VOLUNTEER_DB_URL = "sqlite+aiosqlite:///./volunteer_plus.db"
USER_DB_URL = "sqlite+aiosqlite:///./users.db"

volunteer_engine = create_async_engine(VOLUNTEER_DB_URL, echo=False)
user_engine = create_async_engine(USER_DB_URL, echo=False)

def now_utc():
    return datetime.now(timezone.utc)



async def seed_all():
    print("=" * 60)
    print("SEED DATABASE – Volunteer+")
    print("=" * 60)

    async with get_user_session() as session:
        await seed_users(session)
        await session.commit()

    async with get_volunteer_session() as session:
        await seed_categories(session)
        await seed_organizations(session)
        await seed_events(session)
        await seed_participations(session)
        await seed_subscriptions(session)
        await seed_chats(session)
        await seed_analytics(session)
        await session.commit()

    async with volunteer_engine.begin() as conn:
        await conn.run_sync(OrgBase.metadata.create_all)
        await conn.run_sync(EventBase.metadata.create_all)
        await conn.run_sync(SubBase.metadata.create_all)
        await conn.run_sync(ChatBase.metadata.create_all)
        await conn.run_sync(AnalyticsBase.metadata.create_all)

    async with user_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)

    async with user_engine.connect() as conn:
        await conn.execute(User.__table__.delete())
        await conn.commit()

    async with volunteer_engine.connect() as conn:
        await conn.execute(Organization.__table__.delete())
        await conn.execute(Category.__table__.delete())
        await conn.execute(Event.__table__.delete())
        await conn.execute(Subscription.__table__.delete())
        await conn.execute(Chat.__table__.delete())
        await conn.execute(ChatMember.__table__.delete())
        await conn.execute(Message.__table__.delete())
        await conn.execute(VolunteerStats.__table__.delete())
        await conn.execute(MonthlyStats.__table__.delete())
        await conn.execute(PreferredRole.__table__.delete())
        await conn.commit()

    print("Базы данных успешно заполнены")
    print("\nТестовые учётные данные:")
    print("   user1@example.com / password123  (волонтёр)")
    print("   user2@example.com / password123  (волонтёр)")
    print("   admin@example.com / admin123     (организатор)")

async def get_user_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(user_engine) as session:
        yield session

async def get_volunteer_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(volunteer_engine) as session:
        yield session

# ----- Вспомогательные функции -----
async def seed_users(session):
    print("Добавление пользователей...")
    users = [
        User(id=1, email="user1@example.com", password_hash=hash_password("password123"),
             full_name="Иван Петров", phone="+79991111111", role=UserRoleEnum.VOLUNTEER,
             is_active=True, is_verified=True, created_at=now_utc(), last_login=now_utc()),
        User(id=2, email="user2@example.com", password_hash=hash_password("password123"),
             full_name="Мария Сидорова", phone="+79992222222", role=UserRoleEnum.VOLUNTEER,
             is_active=True, is_verified=True, created_at=now_utc(), last_login=now_utc()),
        User(id=3, email="admin@example.com", password_hash=hash_password("admin123"),
             full_name="Алексей Администратор", phone="+79993333333", role=UserRoleEnum.ADMIN,
             is_active=True, is_verified=True, created_at=now_utc(), last_login=now_utc()),
    ]
    for u in users:
        session.add(u)
        session.add(UserSettings(user_id=u.id, search_radius_km=10, language="ru", theme="light"))
        session.add(UserLocation(user_id=u.id, latitude=55.7558, longitude=37.6173, accuracy=10.0, updated_at=now_utc()))
    print(f"   {len(users)} пользователей")

async def seed_categories(session):
    print("Категории...")
    cats = [
        Category(id=1, name="Экология"),
        Category(id=2, name="Помощь детям"),
        Category(id=3, name="Помощь пожилым"),
        Category(id=4, name="Защита животных"),
        Category(id=5, name="Образование"),
    ]
    for c in cats:
        session.add(c)
    print(f"   {len(cats)} категорий")

async def seed_organizations(session):
    print("Организации...")
    orgs = [
        Organization(id=1, name="Эко-Движение", description="Защита окружающей среды", is_verified=True, rating=4.9, category_id=1, owner_user_id=3),
        Organization(id=2, name="Дети-Герои", description="Помощь детям в трудной ситуации", is_verified=True, rating=4.7, category_id=2, owner_user_id=3),
        Organization(id=3, name="Помощь пожилым", description="Забота о старшем поколении", is_verified=True, rating=4.5, category_id=3, owner_user_id=3),
        Organization(id=4, name="Защита животных", description="Приют для бездомных животных", is_verified=False, rating=4.2, category_id=4, owner_user_id=3),
        Organization(id=5, name="Образование для всех", description="Бесплатные курсы", is_verified=True, rating=4.8, category_id=5, owner_user_id=3),
    ]
    for o in orgs:
        session.add(o)
    print(f"   {len(orgs)} организаций")

async def seed_events(session):
    print("Мероприятия...")
    now = now_utc()
    events = [
        Event(id=1, org_id=1, title="Уборка парка Горького", description="Ежемесячная уборка", start_date=now + timedelta(days=3), end_date=now + timedelta(days=3, hours=4), location="Парк Горького", max_participants=50, qr_secret="qr_secret_1"),
        Event(id=2, org_id=1, title="Посадка деревьев", description="Озеленение", start_date=now + timedelta(days=10), end_date=now + timedelta(days=10, hours=5), location="Сквер Вернисаж", max_participants=30, qr_secret="qr_secret_2"),
        Event(id=3, org_id=2, title="Праздник для детей", description="Концерт и игры", start_date=now + timedelta(days=5), end_date=now + timedelta(days=5, hours=6), location="Детский дом №5", max_participants=20, qr_secret="qr_secret_3"),
        Event(id=4, org_id=3, title="Помощь в доме престарелых", description="Концерт и общение", start_date=now + timedelta(days=7), end_date=now + timedelta(days=7, hours=4), location="Дом престарелых", max_participants=15, qr_secret="qr_secret_4"),
        Event(id=5, org_id=4, title="Выгул собак", description="Прогулка с собаками из приюта", start_date=now + timedelta(days=2), end_date=now + timedelta(days=2, hours=3), location="Приют 'Лучший друг'", max_participants=10, qr_secret="qr_secret_5"),
        Event(id=6, org_id=1, title="Субботник (прошедшее)", description="Уборка в прошлом", start_date=now - timedelta(days=20), end_date=now - timedelta(days=20, hours=4), location="Парк Горького", max_participants=50, qr_secret="qr_secret_6"),
        Event(id=7, org_id=5, title="Курс 'Волонтёрство 101'", description="Обучение", start_date=now + timedelta(days=15), end_date=now + timedelta(days=17), location="Online", max_participants=100, qr_secret="qr_secret_7"),
    ]
    for e in events:
        session.add(e)
    print(f"   {len(events)} мероприятий")

async def seed_participations(session):
    print("Участия в мероприятиях...")
    # user1 зарегистрирован и отметился на 1, 2, 6
    parts = [
        Participation(event_id=1, user_id=1, status=ParticipationStatus.CHECKED_IN, registered_at=now_utc() - timedelta(days=1), checked_in_at=now_utc() - timedelta(days=1)),
        Participation(event_id=2, user_id=1, status=ParticipationStatus.REGISTERED, registered_at=now_utc() - timedelta(days=2)),
        Participation(event_id=6, user_id=1, status=ParticipationStatus.CHECKED_IN, registered_at=now_utc() - timedelta(days=25), checked_in_at=now_utc() - timedelta(days=20)),
        Participation(event_id=3, user_id=2, status=ParticipationStatus.CHECKED_IN, registered_at=now_utc() - timedelta(days=3), checked_in_at=now_utc() - timedelta(days=2)),
    ]
    for p in parts:
        session.add(p)
    print(f"   {len(parts)} участий")

async def seed_subscriptions(session):
    print("Подписки...")
    subs = [
        Subscription(id=1, user_id=1, org_id=1, role="volunteer", active=True),
        Subscription(id=2, user_id=1, org_id=2, role="volunteer", active=True),
        Subscription(id=3, user_id=2, org_id=1, role="volunteer", active=True),
        Subscription(id=4, user_id=2, org_id=4, role="volunteer", active=True),
    ]
    for s in subs:
        session.add(s)
        session.add(SubscriptionLog(user_id=s.user_id, org_id=s.org_id, action="SUBSCRIBE", subscription_id=s.id))
    print(f"   {len(subs)} подписок")

async def seed_chats(session):
    print("Чаты...")
    # Чат с организатором (user1 – admin)
    chat1 = Chat(id=1, chat_type=ChatTypeEnum.ORGANIZER, organization_id=1, is_active=True, created_at=now_utc())
    session.add(chat1)
    session.add(ChatMember(chat_id=1, user_id=1, role="member", joined_at=now_utc()))
    session.add(ChatMember(chat_id=1, user_id=3, role="admin", joined_at=now_utc()))
    # Чат мероприятия #1
    chat2 = Chat(id=2, chat_type=ChatTypeEnum.EVENT, title="Чат: Уборка парка", event_id=1, organization_id=1, is_active=True, created_at=now_utc())
    session.add(chat2)
    session.add(ChatMember(chat_id=2, user_id=1, role="member", joined_at=now_utc()))
    session.add(ChatMember(chat_id=2, user_id=2, role="member", joined_at=now_utc()))
    session.add(ChatMember(chat_id=2, user_id=3, role="admin", joined_at=now_utc()))
    # Сообщения
    msgs = [
        Message(id=1, chat_id=1, sender_id=3, content="Здравствуйте! Готовы помочь?", message_type=MessageTypeEnum.TEXT, is_read=True, created_at=now_utc() - timedelta(hours=2)),
        Message(id=2, chat_id=1, sender_id=1, content="Да, интересует мероприятие по посадке деревьев", message_type=MessageTypeEnum.TEXT, is_read=True, created_at=now_utc() - timedelta(hours=1)),
        Message(id=3, chat_id=2, sender_id=3, content="Встречаемся в 10:00 у главного входа!", message_type=MessageTypeEnum.TEXT, is_read=False, created_at=now_utc() - timedelta(minutes=30)),
    ]
    for m in msgs:
        session.add(m)
    print("   2 чата, 3 сообщения")

async def seed_analytics(session):
    print("Аналитика...")
    # Статистика по организациям (VolunteerStats) – отдельные записи
    stats = [
        VolunteerStats(user_id=1, organization_id=1, role="volunteer", hours_worked=12.0, events_completed=3, last_activity=now_utc()),
        VolunteerStats(user_id=1, organization_id=2, role="volunteer", hours_worked=6.0, events_completed=1, last_activity=now_utc()),
        VolunteerStats(user_id=2, organization_id=1, role="volunteer", hours_worked=4.0, events_completed=1, last_activity=now_utc()),
    ]
    for s in stats:
        session.add(s)

    # Месячная статистика (для графика)
    months = []
    base = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for i in range(6):
        month_date = base - timedelta(days=30*i)
        hours = 8.0 * (6 - i)  # убывающая тенденция для наглядности
        months.append(MonthlyStats(user_id=1, year=month_date.year, month=month_date.month, hours_worked=hours, events_completed=int(hours/4)))
    months.append(MonthlyStats(user_id=2, year=base.year, month=base.month, hours_worked=4.0, events_completed=1))
    for m in months:
        session.add(m)

    # Предпочтительные роли
    roles = [
        PreferredRole(user_id=1, role="volunteer", score=18.0, events_count=4),
        PreferredRole(user_id=1, role="coordinator", score=6.0, events_count=1),
        PreferredRole(user_id=2, role="volunteer", score=4.0, events_count=1),
    ]
    for r in roles:
        session.add(r)

    print(f"   {len(stats)} записей статистики, {len(months)} месяцев, {len(roles)} ролей")

# Запуск
if __name__ == "__main__":
    asyncio.run(seed_all())
