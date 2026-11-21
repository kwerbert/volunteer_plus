import os
import re

from sqlalchemy import MetaData, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateIndex, CreateTable

from app.services.notification_service.config import settings
from app.services.notification_service.db.models import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# SQLAlchemy рендерит: CHECK (notification_type IN ('CHAT', ...))
_OLD_ENUM_CHECK = re.compile(r"notification_type\s+IN\s*\(", re.IGNORECASE)


async def _migrate_notification_type_enum(conn) -> None:
    """Снимает устаревший CHECK с notifications.notification_type (этап 5).

    Без Alembic: SQLite не умеет ALTER CONSTRAINT, поэтому пересобираем
    таблицу с сохранением данных. Идемпотентно — после пересборки CHECK
    на notification_type больше нет.
    """

    def _ddl(sync_conn):
        return sync_conn.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='notifications'"
            )
        ).scalar()

    ddl = await conn.run_sync(_ddl)
    if not ddl or not _OLD_ENUM_CHECK.search(ddl):
        return  # таблицы нет / CHECK уже снят

    def _rebuild(sync_conn):
        table = Base.metadata.tables["notifications"]
        tmp = table.to_metadata(MetaData())
        tmp.name = "notifications_new"

        old_cols = {c["name"] for c in inspect(sync_conn).get_columns("notifications")}
        cols = [c.name for c in tmp.columns if c.name in old_cols]
        col_list = ", ".join(cols)

        # legacy_alter_table: RENAME не должен трогать FK push_logs
        # и не должен падать на временно «висячей» ссылке.
        sync_conn.execute(text("PRAGMA legacy_alter_table=ON"))
        try:
            sync_conn.execute(CreateTable(tmp))  # индексы не эмитятся
            sync_conn.execute(
                text(
                    f"INSERT INTO notifications_new ({col_list}) "
                    f"SELECT {col_list} FROM notifications"
                )
            )
            sync_conn.execute(text("DROP TABLE notifications"))
            sync_conn.execute(
                text("ALTER TABLE notifications_new RENAME TO notifications")
            )
        finally:
            sync_conn.execute(text("PRAGMA legacy_alter_table=OFF"))

        for idx in table.indexes:
            sync_conn.execute(CreateIndex(idx, if_not_exists=True))

    await conn.run_sync(_rebuild)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_notification_type_enum(conn)


async def get_db_session() -> AsyncSession:
    """Dependency для FastAPI: получение сессии БД"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
