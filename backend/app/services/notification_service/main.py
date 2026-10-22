import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notification_service.api.schemas import HealthResponse
from datetime import datetime, timezone
from app.services.notification_service.config import settings
from app.services.notification_service.db.session import engine, async_session_maker
from app.services.notification_service.api.router import router
from app.services.notification_service.db.models import Base
from app.services.notification_service.core.websocket_manager import get_ws_manager

# Логирование
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Общий singleton (на будущее, если понадобится доступ из main)
ws_manager = get_ws_manager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown события"""
    # Startup: создаём таблицы
    logger.info("Starting Notification Service...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    yield

    # Shutdown: закрываем соединения
    logger.info("Shutting down Notification Service...")
    await engine.dispose()


# FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Push + WebSocket notifications for Volunteer+",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Include router
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        timestamp=datetime.now(timezone.utc),
    )

# Middleware для логирования (опционально)
# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     logger.info(f"{request.method} {request.url}")
#     return await call_next(request)

if __name__ == "__main__":
    uvicorn.run(
        "app.services.notification_service.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )