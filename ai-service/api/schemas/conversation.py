"""Pydantic Schemas (DTOs) for the conversation history API."""

from datetime import datetime
from typing import List

from pydantic import BaseModel

from core.domain.message import Session


class SessionResponse(BaseModel):
    """One stored question/answer exchange."""

    session_id: str
    question: str
    answer: str
    response_time_seconds: float
    created_at: datetime

    @classmethod
    def from_domain(cls, session: Session) -> "SessionResponse":
        """Build the response schema from a domain Session."""
        return cls(
            session_id=session.id,
            question=session.question.content,
            answer=session.answer.content,
            response_time_seconds=session.answer.response_time_seconds,
            created_at=session.created_at,
        )


class ConversationResponse(BaseModel):
    """Recent history of one conversation."""

    conversation_id: str
    sessions: List[SessionResponse]
