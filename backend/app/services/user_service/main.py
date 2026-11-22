import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.user_service.api.organizer_router import (
    router as organizer_router,
)
from app.services.user_service.api.router import router
from app.services.user_service.config import get_settings
from app.services.user_service.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting User Service...")
    # Миграции выполняются через Alembic (сервис `migrate` в docker-compose)
    yield
    logger.info("Shutting down User Service...")
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(router)
app.include_router(organizer_router)


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": settings.SERVICE_NAME,
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Эндпоинт проверки здоровья"""
    return {"status": "healthy", "service": settings.SERVICE_NAME}
