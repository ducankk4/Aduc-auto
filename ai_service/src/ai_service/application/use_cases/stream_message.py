"""Use case: stream one chat turn as it is produced (tokens + status events)."""

from __future__ import annotations

from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

from langgraph.graph.state import CompiledStateGraph

from ai_service.application.orchestration.context import AgentContext
from ai_service.domain.actor import AuthContext


async def stream_message(
    graph: CompiledStateGraph,
    session_id: UUID | None,
    message: str,
    auth: AuthContext,
) -> AsyncGenerator[dict[str, Any], None]:
    """Yield `{"type": ..., ...}` events: "session" once, then "token"/"status"
    as the graph runs, then "done".
    """

    resolved_session_id = session_id or uuid4()
    config = {"configurable": {"thread_id": str(resolved_session_id)}}
    context: AgentContext = {"auth_token": auth.token}

    yield {"type": "session", "session_id": str(resolved_session_id)}

    async for mode, chunk in graph.astream(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
        context=context,
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
