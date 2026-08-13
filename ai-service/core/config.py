"""Centralized settings for ai-service loaded from environment variables or .env file.

Every field is declared WITHOUT a default: if a variable is missing, the
application fails at startup with a clear validation error instead of
silently running with a baked-in value. Copy .env.example to .env first.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings shared by every layer of ai-service."""

    APP_ENV: str
    APP_DEBUG: bool

    # Backend API Settings (data source for repository/)
    BACKEND_API_URL: str
    BACKEND_API_TIMEOUT_SECONDS: int

    # LangGraph Checkpointer Settings (SQLite)
    CHECKPOINT_DB_PATH: str

    # LLM Settings (Groq)
    GROQ_API_KEY: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float

    # Vector Store Settings (Qdrant)
    QDRANT_URL: str
    QDRANT_COLLECTION: str

    # Embedding & RAG Settings
    EMBEDDING_MODEL: str
    KNOWLEDGE_DIR: str
    RAG_CHUNK_SIZE: int
    RAG_CHUNK_OVERLAP: int
    RAG_TOP_K: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
