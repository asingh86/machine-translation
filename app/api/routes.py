import logging

from fastapi import APIRouter, HTTPException, Request

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
        registry.translate("hello", "en", "es")
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
    """Translate text between supported language pairs."""
    registry = request.app.state.registry

    try:
        result = registry.translate(body.text, body.source_lang, body.target_lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail="Translation failed unexpectedly")

    return TranslationResponse(
        translated_text=result["translated_text"],
        source_lang=body.source_lang,
        target_lang=body.target_lang,
        model_name=result["model_name"],
        inference_time_ms=result["inference_time_ms"],
    )