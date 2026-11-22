import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.chat_service.api.internal_router import router as internal_router
from app.services.chat_service.api.router import router
from app.services.chat_service.api.websocket_router import (
    websocket_endpoint as ws_endpoint,
)
from app.services.chat_service.config import settings
from app.services.chat_service.db.session import engine

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info("Service-to-Service Auth: API Key (X-Service-Key)")
    yield
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()


app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Микросервис чатов",
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
app.include_router(internal_router)

app.add_api_websocket_route("/ws/chat/{chat_id}", ws_endpoint)


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": settings.SERVICE_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Эндпоинт проверки здоровья"""
    return {"status": "healthy", "service": settings.SERVICE_NAME}


if __name__ == "__main__":
    uvicorn.run(
        "app.services.chat_service.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
    )
