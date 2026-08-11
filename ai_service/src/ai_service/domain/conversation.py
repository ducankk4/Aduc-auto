"""Conversation history as exposed by ai-service, independent of LangGraph's
internal message types (see application/use_cases/get_history.py for the
mapping from BaseMessage to these dataclasses).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ConversationHistory:
    session_id: UUID
    turns: list[Turn]
