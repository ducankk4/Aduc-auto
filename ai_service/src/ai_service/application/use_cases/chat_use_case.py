"""Use case: chat session lifecycle - send a message, stream a reply, read history.

All three actions share the same injected dependency (the compiled LangGraph
graph), which is why they live as methods on one class instead of three
free functions - see code-style.md section 5.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from ai_service.application.dto.chat import ChatResultDTO, ConversationHistoryDTO, MessageDTO
from ai_service.application.orchestration.context import AgentContext
from ai_service.domain.actor import AuthContext
from ai_service.domain.exceptions import ConversationNotFoundError


class ChatUseCase:
    """Use cases for one chat session, backed by a single compiled LangGraph graph."""

    def __init__(self, graph: CompiledStateGraph):
        self._graph = graph

    async def send_message(
        self, session_id: UUID | None, message: str, auth: AuthContext
    ) -> ChatResultDTO:
        """Run one turn of the conversation and return the assistant's reply."""
        resolved_session_id = session_id or uuid4()
        result = await self._graph.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=self._thread_config(resolved_session_id),
            context=self._agent_context(auth),
        )
        reply = self._extract_reply(result["messages"])
        return ChatResultDTO(session_id=resolved_session_id, reply=reply)

    async def stream_message(
        self, session_id: UUID | None, message: str, auth: AuthContext
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield `{"type": ..., ...}` events: "session" once, then "token"/"status"
        as the graph runs, then "done".
        """
        resolved_session_id = session_id or uuid4()
        yield {"type": "session", "session_id": str(resolved_session_id)}

        async for mode, chunk in self._graph.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=self._thread_config(resolved_session_id),
            context=self._agent_context(auth),
            stream_mode=["messages", "custom"],
        ):
            if mode == "messages":
                message_chunk, _metadata = chunk
                token = getattr(message_chunk, "content", None)
                if token:
                    yield {"type": "token", "content": token}
            elif mode == "custom":
                yield {"type": "status", "content": chunk}

        yield {"type": "done", "session_id": str(resolved_session_id)}

    async def get_history(self, session_id: UUID) -> ConversationHistoryDTO:
        """Read back a conversation's messages for GET /chat/{session_id}."""
        state = await self._graph.aget_state(self._thread_config(session_id))

        messages = state.values.get("messages", []) if state.values else []
        if not messages:
            raise ConversationNotFoundError(f"Conversation not found for session_id={session_id}.")

        history = [
            MessageDTO(role=self._role_of(msg), content=self._content_of(msg))
            for msg in messages
            if isinstance(msg, (HumanMessage, AIMessage)) and msg.content
        ]
        return ConversationHistoryDTO(session_id=session_id, messages=history)

    @staticmethod
    def _thread_config(session_id: UUID) -> dict:
        return {"configurable": {"thread_id": str(session_id)}}

    @staticmethod
    def _agent_context(auth: AuthContext) -> AgentContext:
        return {"auth_token": auth.token}

    @staticmethod
    def _extract_reply(messages: list) -> str:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content if isinstance(msg.content, str) else str(msg.content)
        return ""

    @staticmethod
    def _role_of(msg: HumanMessage | AIMessage) -> str:
        return "user" if isinstance(msg, HumanMessage) else "assistant"

    @staticmethod
    def _content_of(msg: HumanMessage | AIMessage) -> str:
        return msg.content if isinstance(msg.content, str) else str(msg.content)
