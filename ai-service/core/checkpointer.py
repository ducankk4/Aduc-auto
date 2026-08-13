"""SQLite-backed LangGraph checkpointer for ai-service.

Persisting graph state is what makes HITL possible: when a sensitive tool
triggers `interrupt()`, the whole graph state is saved here so the run can
be resumed later with `Command(resume=...)` on the same thread_id.

Usage (entry point / lifespan):

    async with open_checkpointer() as checkpointer:
        graph = build_supervisor_graph(checkpointer=checkpointer)
        ...
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger

from core.config import settings


@asynccontextmanager
async def open_checkpointer() -> AsyncIterator[AsyncSqliteSaver]:
    """Open the SQLite checkpointer for the lifetime of the application.

    The underlying aiosqlite connection is opened on enter and closed on
    exit, so this must wrap the whole app lifetime (lifespan/entry point),
    not individual requests.

    Yields:
        AsyncSqliteSaver: Checkpointer ready to be passed to graph.compile().
    """
    async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH) as saver:
        logger.info("SQLite checkpointer opened [path={}]", settings.CHECKPOINT_DB_PATH)
        yield saver
    logger.info("SQLite checkpointer closed [path={}]", settings.CHECKPOINT_DB_PATH)
