"""Chat routes: run a turn, and resume one halted for human approval."""

import time
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger

from agent.history import build_agent_messages
from agent.human_in_the_loop import build_decision, build_resume_command, pending_approvals
from api.response import success
from api.schemas.chat import ApprovalRequest, ChatRequest, ChatResponse, ResumeRequest
from core.exceptions import NotFoundError
from core.masking import mask_sensitive_args

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


def _extract_reply(result: Dict[str, Any]) -> str:
    """Pull the final assistant text out of an invoke result."""
    reply = result["messages"][-1].content
    return reply if isinstance(reply, str) else str(reply)


def _log_interrupts(session_id: str, approvals: List[Dict[str, Any]]) -> None:
    """Audit-log every sensitive tool call halted for review."""
    for approval in approvals:
        logger.info(
            "HITL interrupt [thread_id={}, tool={}, args={}]",
            session_id,
            approval["tool"],
            mask_sensitive_args(approval["args"]),
        )


def _interrupted_response(
    conversation_id: str, session_id: str, approvals: List[Dict[str, Any]]
) -> JSONResponse:
    """Build the response telling the client this turn awaits approval."""
    data = ChatResponse(
        conversation_id=conversation_id,
        session_id=session_id,
        interrupted=True,
        approval_requests=[ApprovalRequest(**approval) for approval in approvals],
    )
    return success(data=data.model_dump())


@chat_router.post("")
async def chat(payload: ChatRequest, request: Request) -> JSONResponse:
    """Run one chat turn; a sensitive tool call halts it for approval.

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

    approvals = pending_approvals(result)
    if approvals:
        _log_interrupts(session_id, approvals)
        await message_service.append_pending_session(
            conversation_id=conversation_id,
            session_id=session_id,
            question=payload.message,
            user_id=payload.user_id,
        )
        logger.info(
            "Chat turn interrupted [conversation_id={}, session_id={}]",
            conversation_id,
            session_id,
        )
        return _interrupted_response(conversation_id, session_id, approvals)

    reply = _extract_reply(result)
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


@chat_router.post("/resume")
async def resume(payload: ResumeRequest, request: Request) -> JSONResponse:
    """Apply human decisions to a halted turn and finish (or re-halt) it.

    The graph resumes on thread_id = session_id of the halted turn; any
    other id would silently start a fresh thread, so the pending
    interrupt is verified before resuming.
    """
    supervisor = request.app.state.supervisor
    message_service = request.app.state.message_service
    config = {"configurable": {"thread_id": payload.session_id}}

    state = await supervisor.aget_state(config)
    if not state.interrupts:
        raise NotFoundError(
            f"Không có yêu cầu phê duyệt nào đang chờ cho lượt: {payload.session_id}"
        )

    decisions = []
    for decision in payload.decisions:
        logger.info(
            "HITL decision [thread_id={}, decision={}, tool={}, args={}]",
            payload.session_id,
            decision.type,
            decision.tool,
            mask_sensitive_args(decision.args or {}),
        )
        decisions.append(
            build_decision(
                decision.type,
                tool=decision.tool,
                args=decision.args,
                message=decision.message,
            )
        )

    started_at = time.perf_counter()
    result = await supervisor.ainvoke(build_resume_command(decisions), config)
    response_time_seconds = time.perf_counter() - started_at

    approvals = pending_approvals(result)
    if approvals:
        # The model asked for another sensitive call: the session stays
        # pending and the client goes through approval again.
        _log_interrupts(payload.session_id, approvals)
        return _interrupted_response(payload.conversation_id, payload.session_id, approvals)

    reply = _extract_reply(result)
    await message_service.complete_session(
        conversation_id=payload.conversation_id,
        session_id=payload.session_id,
        answer=reply,
        response_time_seconds=response_time_seconds,
    )
    logger.info(
        "Resume done [conversation_id={}, session_id={}, seconds={:.2f}]",
        payload.conversation_id,
        payload.session_id,
        response_time_seconds,
    )

    data = ChatResponse(
        conversation_id=payload.conversation_id,
        session_id=payload.session_id,
        reply=reply,
    )
    return success(data=data.model_dump())
