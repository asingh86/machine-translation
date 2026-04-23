from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI

from app.api.routes import router
from app.config import Settings
from app.logging_config import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.safeguard import Safeguard
from app.models.registry import ModelRegistry

settings = Settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, clean up on shutdown."""
    registry = ModelRegistry(settings)
    registry.load()
    app.state.registry = registry
    app.state.settings = settings
    app.state.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    app.state.safeguard = Safeguard(
        min_length=settings.min_input_length,
        max_length=settings.max_input_length,
    )
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

app.add_middleware(RequestLoggingMiddleware)
app.include_router(router)