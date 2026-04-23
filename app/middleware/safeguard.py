import logging
import re

logger = logging.getLogger(__name__)

# Baseline blocklist — in production this would be loaded from a config file
# or external service and be far more comprehensive
BLOCKLIST = {
    "en": {"fuck", "shit", "bitch", "asshole", "bastard", "dick", "cunt"},
    "es": {"puta", "mierda", "coño", "cabrón", "joder", "pendejo"},
}


class SafeguardError(Exception):
    """Raised when content fails a safeguard check."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class Safeguard:
    """Validates and filters translation inputs and outputs.

    Checks applied:
    - Input length within configured bounds
    - Whitespace-only rejection
    - Blocklist-based content filtering on both input and output
    """

    def __init__(self, min_length: int = 1, max_length: int = 5000) -> None:
        self._min_length = min_length
        self._max_length = max_length

    def validate_input(self, text: str, source_lang: str) -> None:
        """Run all input checks. Raises SafeguardError on failure."""
        self._check_length(text)
        self._check_whitespace(text)
        self._check_blocklist(text, source_lang, direction="input")

    def validate_output(self, text: str, target_lang: str) -> None:
        """Run all output checks. Raises SafeguardError on failure."""
        self._check_blocklist(text, target_lang, direction="output")

    def _check_length(self, text: str) -> None:
        if len(text) < self._min_length:
            raise SafeguardError("Text is too short")
        if len(text) > self._max_length:
            raise SafeguardError(
                f"Text exceeds maximum length of {self._max_length} characters"
            )

    def _check_whitespace(self, text: str) -> None:
        if not text.strip():
            raise SafeguardError("Text contains only whitespace")

    def _check_blocklist(self, text: str, lang: str, direction: str) -> None:
        """Check text against language-specific blocklist.

        Uses word boundary matching to avoid false positives on
        substrings (e.g. 'assistant' should not be flagged).
        """
        words = BLOCKLIST.get(lang, set())
        if not words:
            return

        text_lower = text.lower()
        for word in words:
            pattern = rf"\b{re.escape(word)}\b"
            if re.search(pattern, text_lower):
                logger.warning(
                    "Blocked %s: content flagged by safeguard filter [lang=%s]",
                    direction,
                    lang,
                )
                raise SafeguardError(f"Content flagged as inappropriate ({direction})")