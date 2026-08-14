"""Chat router: one endpoint driving the supervisor agent."""

import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger

from agent.history import build_agent_messages
from api.response import success
from api.schemas.chat import ChatRequest, ChatResponse

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.post("")
async def chat(payload: ChatRequest, request: Request) -> JSONResponse:
    """Run one chat turn against the supervisor agent.

    Every turn gets its own thread_id, so earlier turns are replayed from
    stored history instead of coming from the checkpointer.
    """
    supervisor = request.app.state.supervisor
    message_service = request.app.state.message_service

    conversation_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    session_id = f"sess-{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": session_id}}

    history = await message_service.get_recent_sessions(conversation_id)
    logger.info(
        "Chat turn started [conversation_id={}, session_id={}, history_sessions={}]",
        conversation_id,
        session_id,
        len(history),
    )

    started_at = time.perf_counter()
    result = await supervisor.ainvoke(
        {"messages": build_agent_messages(history, payload.message)},
        config,
    )
    response_time_seconds = time.perf_counter() - started_at

    reply = result["messages"][-1].content
    if not isinstance(reply, str):
        reply = str(reply)

    await message_service.append_session(
        conversation_id=conversation_id,
        session_id=session_id,
        question=payload.message,
        answer=reply,
        response_time_seconds=response_time_seconds,
        user_id=payload.user_id,
    )
    logger.info(
        "Chat turn done [conversation_id={}, session_id={}, seconds={:.2f}]",
        conversation_id,
        session_id,
        response_time_seconds,
    )

    data = ChatResponse(conversation_id=conversation_id, session_id=session_id, reply=reply)
    return success(data=data.model_dump())
