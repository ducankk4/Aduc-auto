"""LangGraph checkpointer factory. Uses SQLite for Phase 0 (see
docs/roadmap-ai-service.md section 12) — swap for a Postgres-backed saver
once PendingAction (Phase 2) needs durability beyond local dev.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ai_service.config import Settings


@asynccontextmanager
async def build_checkpointer(settings: Settings) -> AsyncIterator[AsyncSqliteSaver]:
    """Open the checkpointer for the lifetime of the app (see bootstrap/app_factory.py)."""

    Path(settings.checkpoint_sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_sqlite_path) as saver:
        yield saver
