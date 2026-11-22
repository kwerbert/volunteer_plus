import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.event_service.api.internal_router import router as internal_router
from app.services.event_service.api.router import router
from app.services.event_service.config import settings
from app.services.event_service.core.lifecycle import maintenance_loop
from app.services.event_service.db.session import engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    maintenance_task = None
    if settings.MAINTENANCE_ENABLED:
        maintenance_task = asyncio.create_task(maintenance_loop())
        logger.info(
            "Event maintenance loop started (interval=%ss, retention=%s days)",
            settings.MAINTENANCE_INTERVAL_SECONDS,
            settings.CANCELLED_RETENTION_DAYS,
        )
    yield
    if maintenance_task is not None:
        maintenance_task.cancel()
        with suppress(asyncio.CancelledError):
            await maintenance_task
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()


app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Микросервис управления мероприятиями",
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
        "app.services.event_service.main:app", host="0.0.0.0", port=8003, reload=True
    )
