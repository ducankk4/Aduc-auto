"""Conversation history domain entities.

Separate from the LangGraph checkpointer: that one persists execution state
so an interrupted run can resume within a single turn, this one is the
business-readable record used to feed earlier turns back to the agent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MessageRole(str, Enum):
    """Who produced a message."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class UserMessage:
    """A question sent by the user."""

    content: str
    created_at: datetime
    role: MessageRole = MessageRole.USER


@dataclass(frozen=True)
class AssistantMessage:
    """An answer produced by the agent, with how long it took to generate."""

    content: str
    created_at: datetime
    response_time_seconds: float
    role: MessageRole = MessageRole.ASSISTANT


class SessionStatus(str, Enum):
    """Lifecycle of one exchange.

    PENDING_APPROVAL means a sensitive tool interrupted the turn and no
    answer exists yet; sessions abandoned mid-approval stay in this state.
    """

    COMPLETED = "completed"
    PENDING_APPROVAL = "pending_approval"


@dataclass(frozen=True)
class Session:
    """One question/answer exchange. Its id is the LangGraph thread_id."""

    id: str
    question: UserMessage
    created_at: datetime
    answer: Optional[AssistantMessage] = None
    status: SessionStatus = SessionStatus.COMPLETED


@dataclass(frozen=True)
class Conversation:
    """Every session a user has had in one continuous chat."""

    id: str
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None
    sessions: List[Session] = field(default_factory=list)
