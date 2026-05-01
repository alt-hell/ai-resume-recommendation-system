"""
config.py
---------
Application configuration loaded from environment variables / .env file.
All settings are accessed via the singleton `settings` object.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the AI Resume Recommendation System.
    Values are read from environment variables, then .env file, then defaults.
    """

    # ── App ─────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Resume Recommendation System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── MongoDB ──────────────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "resume_system"

    # ── File Upload ──────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"

    # ── ML Model ─────────────────────────────────────────────────────────────
    MODEL_PATH: str = str(Path(__file__).parent / "models" / "model.pkl")
    VECTORIZER_PATH: str = str(Path(__file__).parent / "models" / "vectorizer.pkl")

    # ── Security (JWT) ───────────────────────────────────────────────────────
    SECRET_KEY: str = "changeme-use-a-strong-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    # ── External Integrations ────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openrouter/free"
    RAPIDAPI_KEY: str = ""
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


# Convenience export
settings = get_settings()
