#!/usr/bin/env python3
"""Создаёт тестовую БД для pytest"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROD_URL = (
    "postgresql+asyncpg://volunteer:volunteer_secret_change_me@localhost:5432/postgres"
)


async def main():
    engine = create_async_engine(PROD_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        try:
            await conn.execute(text("CREATE DATABASE volunteer_plus_test;"))
            print("✓ БД volunteer_plus_test создана")
        except Exception as e:
            if "already exists" in str(e):
                print("ℹ БД volunteer_plus_test уже существует")
            else:
                raise
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
