import pytest

from app.config import Settings
from app.models.registry import ModelRegistry


@pytest.fixture(scope="module")
def registry():
    """Load models once for all registry tests — slow but realistic."""
    settings = Settings()
    reg = ModelRegistry(settings)
    reg.load()
    return reg


class TestModelLoading:
    def test_registry_is_ready_after_load(self, registry):
        assert registry.is_ready is True

    def test_list_languages_returns_configured_pairs(self, registry):
        pairs = registry.list_languages()
        assert len(pairs) > 0
        assert {"source": "en", "target": "es"} in pairs

    def test_get_model_returns_tuple(self, registry):
        model, tokenizer = registry.get_model("en", "es")
        assert model is not None
        assert tokenizer is not None

    def test_get_model_unsupported_pair_raises(self, registry):
        with pytest.raises(ValueError, match="Unsupported"):
            registry.get_model("en", "zz")

    def test_unsupported_pair_lists_available(self, registry):
        with pytest.raises(ValueError, match="en→es"):
            registry.get_model("en", "zz")


class TestTranslation:
    def test_translate_returns_expected_keys(self, registry):
        result = registry.translate("Hello", "en", "es")
        assert "translated_text" in result
        assert "model_name" in result
        assert "inference_time_ms" in result

    def test_translate_produces_non_empty_output(self, registry):
        result = registry.translate("Good morning", "en", "es")
        assert len(result["translated_text"]) > 0

    def test_translate_returns_positive_inference_time(self, registry):
        result = registry.translate("Hello", "en", "es")
        assert result["inference_time_ms"] > 0

    def test_translate_includes_model_name(self, registry):
        result = registry.translate("Hello", "en", "es")
        assert "opus-mt-en-es" in result["model_name"]

    def test_translate_unsupported_pair_raises(self, registry):
        with pytest.raises(ValueError):
            registry.translate("Hello", "en", "zz")

    def test_translate_reverse_direction(self, registry):
        result = registry.translate("Hola", "es", "en")
        assert len(result["translated_text"]) > 0

    def test_translate_special_characters(self, registry):
        result = registry.translate("Hello! How are you? :)", "en", "es")
        assert len(result["translated_text"]) > 0

    def test_translate_unicode(self, registry):
        result = registry.translate("Café résumé naïve", "en", "es")
        assert len(result["translated_text"]) > 0


class TestFailedLoad:
    def test_load_with_invalid_pair_raises_if_none_succeed(self):
        settings = Settings()
        settings.default_language_pairs = [("xx", "yy")]
        reg = ModelRegistry(settings)
        with pytest.raises(RuntimeError, match="No models loaded"):
            reg.load()

    def test_registry_not_ready_before_load(self):
        reg = ModelRegistry(Settings())
        assert reg.is_ready is False