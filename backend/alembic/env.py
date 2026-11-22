import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.services.analytics_service.db.models  # noqa: F401
import app.services.chat_service.db.models  # noqa: F401
import app.services.event_service.db.models  # noqa: F401
import app.services.feed_service.db.models  # noqa: F401
import app.services.notification_service.db.models  # noqa: F401
import app.services.organization_service.db.models  # noqa: F401
import app.services.subscription_service.db.models  # noqa: F401

# Каждый импорт регистрирует таблицы в Base.metadata
import app.services.user_service.db.models  # noqa: F401
from alembic import context

# ── Импорт общего Base и ВСЕХ моделей ─────────────────────
from app.db.base import Base  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Переопределяем URL из переменной окружения (если задана)
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    """Миграции в 'offline' режиме — генерация SQL без подключения."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
