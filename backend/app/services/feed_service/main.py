from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.services.feed_service.config import settings
from app.services.feed_service.api.routes import router as api_router
from app.services.feed_service.db.session import init_db, engine
from app.services.feed_service.core.http_client import http_client_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

__version__ = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: инициализация и очистка ресурсов.
    ✅ Создаёт единый aiohttp.ClientSession для всех запросов.
    """
    # === Startup ===
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Cache enabled: {settings.CACHE_ENABLED}")

    # Инициализация БД
    await init_db()
    logger.info("Database tables checked/created")

    # Инициализация пула HTTP-сессий
    await http_client_manager.create_session()
    logger.info("HTTP connection pool initialized")

    yield

    # === Shutdown ===
    logger.info(f"Shutting down {settings.SERVICE_NAME}")

    # Закрытие БД
    await engine.dispose()

    # Закрытие HTTP-сессий (критично для предотвращения утечек!)
    await http_client_manager.close_session()
    logger.info("HTTP connection pool closed")


app = FastAPI(
    title=f"{settings.SERVICE_NAME} - Volunteer+ API",
    description="Микросервис главной страницы: персонализированная лента мероприятий",
    version=__version__,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://10.0.2.2:3000",
        "http://10.0.2.2:8001",
        "http://10.0.2.2:8008",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1", tags=["Feed"])


@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "status": "running",
        "version": __version__,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": __version__
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.services.feed_service.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )