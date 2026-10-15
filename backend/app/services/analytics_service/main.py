from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
from app.services.analytics_service.config import settings
from app.services.analytics_service.api.router import router
from app.services.analytics_service.db.session import init_db, engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager для startup/shutdown событий"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    await init_db()
    logger.info("Database tables checked/created")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()


app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Микросервис аналитики волонтёрства",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


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
        "app.services.analytics_service.main:app",
        host="0.0.0.0",
        port=8005,
        reload=True
    )