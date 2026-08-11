"""Use case: send one chat message and get the assistant's full reply."""

from __future__ import annotations

from uuid import UUID, uuid4

from langchain_core.messages import AIMessage
from langgraph.graph.state import CompiledStateGraph

from ai_service.application.dto.chat import ChatResultDTO
from ai_service.application.orchestration.context import AgentContext
from ai_service.domain.actor import AuthContext


async def send_message(
    graph: CompiledStateGraph,
    session_id: UUID | None,
    message: str,
    auth: AuthContext,
) -> ChatResultDTO:
    """Run one turn of the conversation and return the assistant's reply."""

    resolved_session_id = session_id or uuid4()
    config = {"configurable": {"thread_id": str(resolved_session_id)}}
    context: AgentContext = {"auth_token": auth.token}

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
        context=context,
    )
    reply = _extract_reply(result["messages"])
    return ChatResultDTO(session_id=resolved_session_id, reply=reply)


def _extract_reply(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""
