from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager  # добавить
import logging
import uvicorn
from app.services.event_service.config import settings
from app.services.event_service.api.router import router
from app.services.event_service.db.session import init_db, engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ДОБАВИТЬ lifespan-менеджер
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    await init_db()
    logger.info("Database tables checked/created")
    yield
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()

app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Микросервис управления мероприятиями",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # добавить
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# УДАЛИТЬ @app.on_event("startup") и @app.on_event("shutdown")

@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.services.event_service.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )