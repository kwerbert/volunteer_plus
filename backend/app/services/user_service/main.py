"""Точка входа User Service"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.user_service.api.organizer_router import (
    router as organizer_router,  # ✅ ДОБАВИТЬ
)
from app.services.user_service.api.router import router
from app.services.user_service.config import get_settings
from app.services.user_service.db.session import engine, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """События запуска и остановки приложения"""
    # Startup
    logger.info("Starting User Service...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
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
app.include_router(organizer_router)  # ✅ ДОБАВИТЬ ЭТУ СТРОКУ


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
