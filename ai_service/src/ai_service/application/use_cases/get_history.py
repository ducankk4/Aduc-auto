"""Use case: read back a conversation's turns for GET /chat/{session_id}."""

from __future__ import annotations

from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from ai_service.domain.conversation import ConversationHistory, Turn
from ai_service.domain.exceptions import ConversationNotFoundError


async def get_history(graph: CompiledStateGraph, session_id: UUID) -> ConversationHistory:
    config = {"configurable": {"thread_id": str(session_id)}}
    state = await graph.aget_state(config)

    messages = state.values.get("messages", []) if state.values else []
    if not messages:
        raise ConversationNotFoundError(f"Không tìm thấy hội thoại với session_id={session_id}.")

    turns = [
        Turn(role=_role_of(msg), content=_content_of(msg))
        for msg in messages
        if isinstance(msg, (HumanMessage, AIMessage)) and msg.content
    ]
    return ConversationHistory(session_id=session_id, turns=turns)


def _role_of(msg: HumanMessage | AIMessage) -> str:
    return "user" if isinstance(msg, HumanMessage) else "assistant"


def _content_of(msg: HumanMessage | AIMessage) -> str:
    return msg.content if isinstance(msg.content, str) else str(msg.content)
