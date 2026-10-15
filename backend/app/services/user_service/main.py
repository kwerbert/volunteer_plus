"""Точка входа User Service"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
from app.services.user_service.config import settings
from app.services.user_service.api.router import router
from app.services.user_service.db.session import init_db, engine

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """События запуска и остановки приложения"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} on {settings.SERVICE_PORT}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"JWT Algorithm: {settings.JWT_ALGORITHM}")
    logger.info(f"Service-to-Service Auth: API Key (X-Service-Key)")
    await init_db()
    logger.info("Database tables checked/created")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()

app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Микросервис аутентификации и управления пользователями Volunteer+",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": settings.SERVICE_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Эндпоинт проверки здоровья"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.services.user_service.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )