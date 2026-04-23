import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

from app.middleware.safeguard import SafeguardError
from app.schemas.translation import (
    HealthResponse,
    LanguagePair,
    TranslationRequest,
    TranslationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok"}


@router.get("/health/live", response_model=HealthResponse)
async def liveness():
    """Liveness probe — is the process running?"""
    return HealthResponse(status="alive")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(request: Request):
    """Readiness probe — are models loaded and working?"""
    registry = request.app.state.registry

    if not registry.is_ready:
        raise HTTPException(status_code=503, detail="Models not yet loaded")

    try:
        await asyncio.to_thread(registry.translate, "hello", "en", "es")
    except Exception:
        logger.exception("Readiness check failed")
        raise HTTPException(status_code=503, detail="Model inference check failed")

    return HealthResponse(status="ready", models_loaded=len(registry.list_languages()))


@router.get("/languages", response_model=list[LanguagePair])
async def list_languages(request: Request):
    """Return all supported language pairs."""
    registry = request.app.state.registry
    return registry.list_languages()


@router.post("/translate", response_model=TranslationResponse)
async def translate(body: TranslationRequest, request: Request):
    """Translate text between supported language pairs.

    Inference is offloaded to a thread pool via asyncio.to_thread so it
    doesn't block the event loop. A semaphore limits concurrent inferences
    to prevent memory exhaustion under load.
    """
    registry = request.app.state.registry
    semaphore = request.app.state.semaphore
    settings = request.app.state.settings
    safeguard = request.app.state.safeguard

    try:
        safeguard.validate_input(body.text, body.source_lang)
    except SafeguardError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        async with semaphore:
            result = await asyncio.wait_for(
                asyncio.to_thread(registry.translate, body.text, body.source_lang, body.target_lang),
                timeout=settings.request_timeout_seconds,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except asyncio.TimeoutError:
        logger.warning("Translation timed out after %ds", settings.request_timeout_seconds)
        raise HTTPException(status_code=504, detail="Translation timed out")
    except Exception:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail="Translation failed unexpectedly")

    try:
        safeguard.validate_output(result["translated_text"], body.target_lang)
    except SafeguardError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TranslationResponse(
        translated_text=result["translated_text"],
        source_lang=body.source_lang,
        target_lang=body.target_lang,
        model_name=result["model_name"],
        inference_time_ms=result["inference_time_ms"],
    )