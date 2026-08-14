from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger

from core.config import settings
from core.domain.message import AssistantMessage, Conversation, Session, UserMessage
from core.interface.repository import IMessageRepository


class MessageService:
    """Use cases for conversation history."""

    def __init__(self, message_repository: IMessageRepository) -> None:
        self._message_repository = message_repository

    async def get_recent_sessions(self, conversation_id: str) -> List[Session]:
        """Return the most recent sessions of a conversation, oldest first.

        Args:
            conversation_id (str): Conversation identifier.

        Returns:
            List[Session]: Up to CONVERSATION_HISTORY_LIMIT sessions, in the
                order they happened, ready to be replayed to the agent.
        """
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
        """Append one question/answer exchange to a conversation.

        Creates the conversation when this is its first session.

        Args:
            conversation_id (str): Conversation the session belongs to.
            session_id (str): Identifier of this exchange (the thread_id).
            question (str): What the user asked.
            answer (str): What the agent replied.
            response_time_seconds (float): How long the answer took.
            user_id (Optional[str]): Who asked, when the caller knows.
        """
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
            conversation = Conversation(
                id=conversation.id,
                created_at=conversation.created_at,
                updated_at=now,
                user_id=user_id or conversation.user_id,
                sessions=[*conversation.sessions, session],
            )
            await self._message_repository.update_conversation(conversation)

        logger.info(
            "Session stored [conversation_id={}, session_id={}, total_sessions={}]",
            conversation_id,
            session_id,
            len(conversation.sessions),
        )
