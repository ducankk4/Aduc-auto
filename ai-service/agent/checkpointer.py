from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger

from core.config import settings as st


@asynccontextmanager
async def open_checkpointer() -> AsyncIterator[AsyncSqliteSaver]:
    """Open the SQLite checkpointer for the lifetime of the application.

    The underlying aiosqlite connection is opened on enter and closed on
    exit, so this must wrap the whole app lifetime (lifespan/entry point),
    not individual requests.

    Yields:
        AsyncSqliteSaver: Checkpointer ready to be passed to graph.compile().
    """
    async with AsyncSqliteSaver.from_conn_string(st.CHECKPOINT_DB_PATH) as saver:
        logger.info("SQLite checkpointer opened [path={}]", st.CHECKPOINT_DB_PATH)
        yield saver
    logger.info("SQLite checkpointer closed [path={}]", st.CHECKPOINT_DB_PATH)
