from pydantic_settings import BaseSettings
 
 
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
 
    app_name: str = "Translation API"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
 
    model_dir: str = "models_cache"
    max_input_length: int = 5000
    min_input_length: int = 1
 
    default_language_pairs: list[tuple[str, str]] = [
        ("en", "es"),
        ("es", "en"),
    ]
 
    max_concurrent_requests: int = 4
    request_timeout_seconds: int = 30
 
    model_config = {"env_prefix": "TRANSLATE_"}
 