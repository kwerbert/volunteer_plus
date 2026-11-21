from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.event_service.config import settings

from .models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def _migrate_event_columns(conn) -> None:
    def _columns(sync_conn):
        return [c["name"] for c in inspect(sync_conn).get_columns("events")]

    columns = await conn.run_sync(_columns)
    additions = {
        "qr_check_enabled": "BOOLEAN NOT NULL DEFAULT 1",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
        "image_url": "VARCHAR(512)",
        "cancelled_at": "DATETIME",
        "has_custom_roles": "BOOLEAN NOT NULL DEFAULT 0",
    }
    for name, ddl in additions.items():
        if name not in columns:
            await conn.execute(text(f"ALTER TABLE events ADD COLUMN {name} {ddl}"))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_event_columns(conn)


async def get_db_session():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
