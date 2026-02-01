"""
Application settings via pydantic-settings.
Loads from environment and optional .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment and feature flags."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://camaral:camaral@localhost:5432/camaral"

    # Google AI (Gemini)
    GOOGLE_API_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Logfire (optional; if set, observability is enabled)
    LOGFIRE_TOKEN: str | None = None
    # Self-hosted / local Logfire backend (e.g. http://localhost:8000). If set, token is sent to this URL.
    LOGFIRE_BASE_URL: str | None = None

    # RAG
    RAG_TOP_K: int = 5
    EMBEDDING_MODEL: str = "text-embedding-004"
    RAG_SIMILARITY_THRESHOLD: float = 1.0  # max L2 distance for top chunk; above = guarded

    # Chat & memory
    CHAT_HISTORY_LIMIT: int = 20
    CONVERSATION_TIMEOUT_SECONDS: int = 3600

    # Rate limiting (per user)
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60


settings = Settings()
