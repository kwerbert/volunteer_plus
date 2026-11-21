from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.analytics_service.config import settings

from .models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def _migrate_analytics_columns(conn) -> None:
    """Идемпотентная миграция без Alembic"""

    def _columns(sync_conn):
        return [c["name"] for c in inspect(sync_conn).get_columns("volunteer_stats")]

    columns = await conn.run_sync(_columns)
    if "organization_name_snapshot" not in columns:
        await conn.execute(
            text(
                "ALTER TABLE volunteer_stats "
                "ADD COLUMN organization_name_snapshot VARCHAR(255)"
            )
        )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_analytics_columns(conn)


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
