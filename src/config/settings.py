"""
Application settings via pydantic-settings.
Loads from environment and optional .env file.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Vertex AI embedding names that are not valid for Gemini API (embedContent); map to Gemini model
_GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
_VERTEX_ONLY_EMBEDDING_NAMES = frozenset(
    {"text-embedding-001", "text-embedding-004", "text-embedding-005", "text-multilingual-embedding-002"}
)


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
    RAG_TOP_K: int = 2  # few chunks to avoid all pages; agent should search with Spanish terms (fundador, etc.) for founder/CEO
    EMBEDDING_MODEL: str = _GEMINI_EMBEDDING_MODEL  # Gemini API; use 768 dims via output_dimensionality
    RAG_SIMILARITY_THRESHOLD: float = 1.0  # max L2 distance per chunk; relaxed so Spanish doc matches English questions

    @field_validator("EMBEDDING_MODEL", mode="after")
    @classmethod
    def normalize_embedding_model(cls, v: str) -> str:
        """Use Gemini embedding model when Vertex-only name is set (e.g. by env var)."""
        if v.strip().lower() in _VERTEX_ONLY_EMBEDDING_NAMES:
            return _GEMINI_EMBEDDING_MODEL
        return v

    # Chat & memory
    CHAT_HISTORY_LIMIT: int = 10  # last N messages; fewer = less context noise
    CONVERSATION_TIMEOUT_SECONDS: int = 3600

    # Rate limiting (per user)
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60


settings = Settings()
