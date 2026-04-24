import pytest

from app.middleware.safeguard import Safeguard, SafeguardError


@pytest.fixture
def safeguard():
    return Safeguard(min_length=1, max_length=100)


class TestInputValidation:
    def test_valid_input_passes(self, safeguard):
        safeguard.validate_input("Hello world", "en")

    def test_empty_string_rejected(self, safeguard):
        with pytest.raises(SafeguardError, match="too short"):
            safeguard.validate_input("", "en")

    def test_whitespace_only_rejected(self, safeguard):
        with pytest.raises(SafeguardError, match="whitespace"):
            safeguard.validate_input("   \n\t  ", "en")

    def test_exceeds_max_length_rejected(self, safeguard):
        with pytest.raises(SafeguardError, match="maximum length"):
            safeguard.validate_input("a" * 101, "en")

    def test_at_max_length_passes(self, safeguard):
        safeguard.validate_input("a" * 100, "en")

    def test_single_char_passes(self, safeguard):
        safeguard.validate_input("a", "en")


class TestBlocklistFiltering:
    def test_clean_text_passes(self, safeguard):
        safeguard.validate_input("Good morning", "en")

    def test_blocked_word_rejected(self, safeguard):
        with pytest.raises(SafeguardError, match="inappropriate"):
            safeguard.validate_input("fuck this", "en")

    def test_blocked_word_case_insensitive(self, safeguard):
        with pytest.raises(SafeguardError, match="inappropriate"):
            safeguard.validate_input("FUCK this", "en")

    def test_substring_not_blocked(self, safeguard):
        """Words like 'assistant' should not trigger on 'ass'."""
        safeguard.validate_input("The assistant helped me", "en")

    def test_spanish_blocked_word_rejected(self, safeguard):
        with pytest.raises(SafeguardError, match="inappropriate"):
            safeguard.validate_input("eres una puta", "es")

    def test_unknown_language_skips_blocklist(self, safeguard):
        safeguard.validate_input("anything goes here", "xx")


class TestOutputValidation:
    def test_clean_output_passes(self, safeguard):
        safeguard.validate_output("Hola mundo", "es")

    def test_blocked_output_rejected(self, safeguard):
        with pytest.raises(SafeguardError, match="inappropriate"):
            safeguard.validate_output("vete a la mierda", "es")