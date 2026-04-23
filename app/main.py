from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI

from app.api.routes import router
from app.config import Settings
from app.models.registry import ModelRegistry

logger = logging.getLogger(__name__)
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, clean up on shutdown."""
    registry = ModelRegistry(settings)
    registry.load()
    app.state.registry = registry
    app.state.settings = settings
    app.state.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    logger.info(
        "Models loaded — application ready (max concurrent requests: %d)",
        settings.max_concurrent_requests,
    )
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(router)