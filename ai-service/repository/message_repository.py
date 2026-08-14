"""Conversation history persisted in SQLite.

The whole Conversation is stored as one JSON blob: it is always read and
written as a unit, and nothing queries individual sessions yet.
"""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Optional

import aiosqlite
from loguru import logger

from core.domain.message import (
    AssistantMessage,
    Conversation,
    MessageRole,
    Session,
    UserMessage,
)
from core.exceptions import InfrastructureError
from core.interface.repository import IMessageRepository

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


class SqliteMessageRepository(IMessageRepository):
    """Conversation history stored in a local SQLite file."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        try:
            async with aiosqlite.connect(self._db_path) as connection:
                await connection.execute(_CREATE_TABLE)
                await connection.commit()
        except aiosqlite.Error as exc:
            raise InfrastructureError(f"Không khởi tạo được kho hội thoại: {exc}") from exc
        logger.info("Conversation store ready [path={}]", self._db_path)

    async def find_conversation(self, conversation_id: str) -> Optional[Conversation]:
        try:
            async with aiosqlite.connect(self._db_path) as connection:
                async with connection.execute(
                    "SELECT data FROM conversations WHERE id = ?", (conversation_id,)
                ) as cursor:
                    row = await cursor.fetchone()
        except aiosqlite.Error as exc:
            raise InfrastructureError(f"Không đọc được hội thoại: {exc}") from exc

        if row is None:
            logger.debug("Conversation not found [conversation_id={}]", conversation_id)
            return None
        return _to_domain(json.loads(row[0]))

    async def create_conversation(self, conversation: Conversation) -> None:
        await self._write(
            "INSERT INTO conversations (id, user_id, data, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            conversation,
        )
        logger.info("Conversation created [conversation_id={}]", conversation.id)

    async def update_conversation(self, conversation: Conversation) -> None:
        await self._write(
            "INSERT INTO conversations (id, user_id, data, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " user_id = excluded.user_id,"
            " data = excluded.data,"
            " updated_at = excluded.updated_at",
            conversation,
        )
        logger.info(
            "Conversation updated [conversation_id={}, sessions={}]",
            conversation.id,
            len(conversation.sessions),
        )

    async def _write(self, statement: str, conversation: Conversation) -> None:
        """Run one INSERT/UPSERT statement with the conversation serialized."""
        payload = json.dumps(asdict(conversation), default=str, ensure_ascii=False)
        try:
            async with aiosqlite.connect(self._db_path) as connection:
                await connection.execute(
                    statement,
                    (
                        conversation.id,
                        conversation.user_id,
                        payload,
                        conversation.created_at.isoformat(),
                        conversation.updated_at.isoformat(),
                    ),
                )
                await connection.commit()
        except aiosqlite.Error as exc:
            raise InfrastructureError(f"Không lưu được hội thoại: {exc}") from exc


def _to_domain(data: Dict[str, Any]) -> Conversation:
    """Rebuild a Conversation from its stored JSON payload."""
    return Conversation(
        id=data["id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        user_id=data.get("user_id"),
        sessions=[_session_to_domain(item) for item in data.get("sessions", [])],
    )


def _session_to_domain(data: Dict[str, Any]) -> Session:
    """Rebuild one Session from its stored JSON payload."""
    question = data["question"]
    answer = data["answer"]
    return Session(
        id=data["id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        question=UserMessage(
            content=question["content"],
            created_at=datetime.fromisoformat(question["created_at"]),
            role=MessageRole(question["role"]),
        ),
        answer=AssistantMessage(
            content=answer["content"],
            created_at=datetime.fromisoformat(answer["created_at"]),
            response_time_seconds=answer["response_time_seconds"],
            role=MessageRole(answer["role"]),
        ),
    )
