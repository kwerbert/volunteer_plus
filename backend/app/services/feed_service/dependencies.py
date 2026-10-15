from sqlalchemy.ext.asyncio import AsyncSession
from .config import Settings, settings as feed_settings
from .db.session import get_db_session

async def get_db() -> AsyncSession:
    async for session in get_db_session():
        yield session

def get_settings() -> Settings:
    return feed_settings