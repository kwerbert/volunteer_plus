import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.organization_service.api.internal_router import (
    router as internal_router,
)
from app.services.organization_service.api.router import router
from app.services.organization_service.config import settings
from app.services.organization_service.db.session import engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Organization Service...")
    # Миграции выполняются через Alembic (сервис `migrate` в docker-compose)
    yield
    logger.info("Shutting down Organization Service...")
    await engine.dispose()


app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Микросервис управления организациями",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(internal_router)

# УДАЛИТЬ старые декораторы @app.on_event("startup") и @app.on_event("shutdown")
# Функции startup_event и shutdown_event больше не нужны


@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


if __name__ == "__main__":
    uvicorn.run(
        "app.services.organization_service.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
    )
