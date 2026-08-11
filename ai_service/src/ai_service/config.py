"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Phase 0 settings only — MODEL_SUBAGENT, AI_DATABASE_URL (Postgres),
    EMBEDDING_ENDPOINT, and PENDING_ACTION_TTL_SECONDS are intentionally
    omitted until the phases that need them (see docs/roadmap-ai-service.md).

    No field has a hardcoded default: every value must come from `.env` /
    the environment, so `.env` stays the single source of truth for config
    instead of duplicating values in code.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str
    app_debug: bool

    backend_base_url: str
    backend_timeout_seconds: float

    anthropic_api_key: str
    model_supervisor: str

    ai_service_port: int

    # Temporary Phase 0 storage; replaced by AI_DATABASE_URL (Postgres) once
    # PendingAction (Phase 2) needs durability beyond local dev.
    checkpoint_sqlite_path: str
