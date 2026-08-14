from dataclasses import replace
from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger

from core.config import settings
from core.domain.message import (
    AssistantMessage,
    Conversation,
    Session,
    SessionStatus,
    UserMessage,
)
from core.exceptions import NotFoundError
from core.interface.repository import IMessageRepository


class MessageService:
    """Use cases for conversation history."""

    def __init__(self, message_repository: IMessageRepository) -> None:
        self._message_repository = message_repository

    async def get_recent_sessions(self, conversation_id: str) -> List[Session]:
        conversation = await self._message_repository.find_conversation(conversation_id)
        if conversation is None:
            return []
        return conversation.sessions[-settings.CONVERSATION_HISTORY_LIMIT :]

    async def append_session(
        self,
        conversation_id: str,
        session_id: str,
        question: str,
        answer: str,
        response_time_seconds: float,
        user_id: Optional[str] = None,
    ) -> None:
        """Store one completed question/answer exchange."""
        now = datetime.now(timezone.utc)
        session = Session(
            id=session_id,
            created_at=now,
            question=UserMessage(content=question, created_at=now),
            answer=AssistantMessage(
                content=answer,
                created_at=now,
                response_time_seconds=response_time_seconds,
            ),
        )
        await self._append(conversation_id, session, user_id)

    async def append_pending_session(
        self,
        conversation_id: str,
        session_id: str,
        question: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Store an exchange interrupted by a sensitive tool, answer still unknown."""
        now = datetime.now(timezone.utc)
        session = Session(
            id=session_id,
            created_at=now,
            question=UserMessage(content=question, created_at=now),
            status=SessionStatus.PENDING_APPROVAL,
        )
        await self._append(conversation_id, session, user_id)

    async def complete_session(
        self,
        conversation_id: str,
        session_id: str,
        answer: str,
        response_time_seconds: float,
    ) -> None:
        """Fill in the answer of a pending session once its turn resumed.

        Raises:
            NotFoundError: If the conversation or the pending session is absent.
        """
        conversation = await self._message_repository.find_conversation(conversation_id)
        if conversation is None:
            raise NotFoundError(f"Không tìm thấy hội thoại: {conversation_id}")

        now = datetime.now(timezone.utc)
        sessions = list(conversation.sessions)
        for index, session in enumerate(sessions):
            if session.id == session_id:
                sessions[index] = replace(
                    session,
                    answer=AssistantMessage(
                        content=answer,
                        created_at=now,
                        response_time_seconds=response_time_seconds,
                    ),
                    status=SessionStatus.COMPLETED,
                )
                break
        else:
            raise NotFoundError(f"Không tìm thấy lượt hội thoại đang chờ: {session_id}")

        await self._message_repository.update_conversation(
            replace(conversation, updated_at=now, sessions=sessions)
        )
        logger.info(
            "Session completed [conversation_id={}, session_id={}]",
            conversation_id,
            session_id,
        )

    async def _append(
        self, conversation_id: str, session: Session, user_id: Optional[str]
    ) -> None:
        """Append one session, creating the conversation on first use."""
        now = session.created_at
        conversation = await self._message_repository.find_conversation(conversation_id)
        if conversation is None:
            conversation = Conversation(
                id=conversation_id,
                created_at=now,
                updated_at=now,
                user_id=user_id,
                sessions=[session],
            )
            await self._message_repository.create_conversation(conversation)
        else:
            conversation = replace(
                conversation,
                updated_at=now,
                user_id=user_id or conversation.user_id,
                sessions=[*conversation.sessions, session],
            )
            await self._message_repository.update_conversation(conversation)

        logger.info(
            "Session stored [conversation_id={}, session_id={}, status={}, total_sessions={}]",
            conversation_id,
            session.id,
            session.status.value,
            len(conversation.sessions),
        )
