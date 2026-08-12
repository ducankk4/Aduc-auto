"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MODEL_SUBAGENT, AI_DATABASE_URL (Postgres), and PENDING_ACTION_TTL_SECONDS
    are intentionally still omitted until the phases that need them (see
    docs/roadmap-ai-service.md). RAG fields were added in Phase 1.

    No field has a hardcoded default: every value must come from `.env` /
    the environment, so `.env` stays the single source of truth for config
    instead of duplicating values in code.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str
    app_debug: bool

    backend_base_url: str
    backend_timeout_seconds: float

    groq_api_key: str
    model_supervisor: str

    ai_service_port: int

    # Temporary Phase 0 storage; replaced by AI_DATABASE_URL (Postgres) once
    # PendingAction (Phase 2) needs durability beyond local dev.
    checkpoint_sqlite_path: str

    # RAG (Phase 1). Qdrant runs as its own service (roadmap 14.5) — separate
    # from AI_DATABASE_URL, which is not introduced yet since nothing else
    # needs Postgres before Phase 2. Embedding is self-hosted in-process via
    # sentence-transformers, so there is no separate embedding service URL.
    qdrant_url: str
    qdrant_collection_name: str
    embedding_model_name: str

    # Directory of markdown FAQ/policy source files ingested by
    # scripts/sync_knowledge.py, relative to the process's working directory
    # unless given as an absolute path.
    knowledge_dir: str


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings instance, parsed from .env exactly once."""
    return Settings()
