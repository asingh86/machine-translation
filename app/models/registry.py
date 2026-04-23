import logging
import time
from typing import TypedDict
from transformers import MarianMTModel, MarianTokenizer
from app.config import Settings

logger = logging.getLogger(__name__)

MODEL_NAME_TEMPLATE = "Helsinki-NLP/opus-mt-{src}-{tgt}"

class TranslationRequest(TypedDict):
    """Structured result from a translation inference."""
    
    translated_text: str
    model_name: str
    inference_time_ms: float

class ModelRegistry:
    """Manages loading, access and inference for translation models"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._models: dict[tuple[str, str], tuple[MarianMTModel, MarianTokenizer]] = {}
        self._ready = False

    @property
    def is_ready(self) -> bool:
        """Whether all models have been loaded successfully."""
        return self._ready
    
    def load(self) -> None:
        """Load all configured language pair models from HuggingFace."""
        failed: list[str] = []

        for source, target in self._settings.default_language_pairs:
            model_name = MODEL_NAME_TEMPLATE.format(src=source, tgt=target)
            logger.info("Loading model: %s", model_name)
 
            try:
                start = time.perf_counter()
                tokenizer = MarianTokenizer.from_pretrained(
                    model_name, cache_dir=self._settings.model_dir
                )
                model = MarianMTModel.from_pretrained(
                    model_name, cache_dir=self._settings.model_dir
                )
                elapsed = time.perf_counter() - start
 
                self._models[(source, target)] = (model, tokenizer)
                logger.info("Loaded %s in %.2fs", model_name, elapsed)
            except Exception:
                logger.exception("Failed to load model: %s", model_name)
                failed.append(model_name)
 
        if not self._models:
            raise RuntimeError(
                f"No models loaded successfully. Failed: {', '.join(failed)}"
            )
 
        if failed:
            logger.warning("Some models failed to load: %s", ", ".join(failed))
 
        self._ready = True
        logger.info("Models loaded: %d succeeded, %d failed", len(self._models), len(failed))

    def get_model(self, source_lang: str, target_lang: str) -> tuple[MarianMTModel, MarianTokenizer]:
        """Retrieve model and tokenizer for a language pair."""
        key = (source_lang, target_lang)
        if key not in self._models:
            available = [f"{s}→{t}" for s, t in self._models]
            raise ValueError(
                f"Unsupported language pair: {source_lang}→{target_lang}. "
                f"Available: {', '.join(available)}"
            )
        return self._models[key]
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationRequest:
        """Translate text and return result with metadata.
 
        Returns:
            dict with keys: translated_text, model_name, inference_time_ms
        """
        model, tokenizer = self.get_model(source_lang, target_lang)
        model_name = MODEL_NAME_TEMPLATE.format(src=source_lang, tgt=target_lang)
 
        start = time.perf_counter()
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        outputs = model.generate(**inputs)
        translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        inference_time_ms = round((time.perf_counter() - start) * 1000, 2)
 
        return {
            "translated_text": translated_text,
            "model_name": model_name,
            "inference_time_ms": inference_time_ms,
        }
    
    def list_languages(self) -> list[dict[str, str]]:
        """Return all supported language pairs."""
        return [
            {"source": src, "target": tgt}
            for src, tgt in self._models
        ]