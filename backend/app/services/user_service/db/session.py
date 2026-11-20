"""Сессии БД User Service"""

from typing import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.user_service.config import get_settings
from app.services.user_service.db.models import Base

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _migrate_roles_and_admin_flag(conn) -> None:
    """Идемпотентная миграция без Alembic:
    1) добавляет users.is_admin, если колонки нет;
    2) старый role='ADMIN' -> role='VOLUNTEER' + is_admin=1.
    """

    def _columns(sync_conn):
        return [c["name"] for c in inspect(sync_conn).get_columns("users")]

    columns = await conn.run_sync(_columns)
    if "is_admin" not in columns:
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
        )

    await conn.execute(
        text("UPDATE users SET is_admin = 1, role = 'VOLUNTEER' WHERE role = 'ADMIN'")
    )


async def init_db() -> None:
    """Создаёт таблицы при старте"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_roles_and_admin_flag(conn)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронный генератор сессий для Depends()"""
    async with async_session_maker() as session:
        yield session
