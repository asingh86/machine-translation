from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    """Request body for the translation endpoint."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to translate",
        examples=["Hello, how are you?"],
    )
    source_lang: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Source language code",
        examples=["en"],
    )
    target_lang: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Target language code",
        examples=["es"],
    )


class TranslationResponse(BaseModel):
    """Response body from the translation endpoint."""

    translated_text: str
    source_lang: str
    target_lang: str
    model_name: str
    inference_time_ms: float


class LanguagePair(BaseModel):
    """A supported language pair."""

    source: str
    target: str


class HealthResponse(BaseModel):
    """Response body for health check endpoints."""

    status: str
    models_loaded: int | None = None