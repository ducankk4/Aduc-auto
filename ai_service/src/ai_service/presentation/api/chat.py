"""Chat endpoints: send a message, stream a reply, read conversation history."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ai_service.application.use_cases.get_history import get_history
from ai_service.application.use_cases.send_message import send_message
from ai_service.application.use_cases.stream_message import stream_message
from ai_service.bootstrap.container import AppContainer
from ai_service.domain.actor import AuthContext
from ai_service.presentation.dependencies import get_auth_context
from ai_service.presentation.envelope import success
from ai_service.presentation.schemas.chat import ChatRequestSchema

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


@chat_router.post("")
async def post_chat(
    payload: ChatRequestSchema,
    container: AppContainer = Depends(get_container),
    auth: AuthContext = Depends(get_auth_context),
):
    result = await send_message(container.graph, payload.session_id, payload.message, auth)
    return success(
        data={
            "session_id": str(result.session_id),
            "reply": result.reply,
            "pending_action": None,
        }
    )


@chat_router.post("/stream")
async def post_chat_stream(
    payload: ChatRequestSchema,
    container: AppContainer = Depends(get_container),
    auth: AuthContext = Depends(get_auth_context),
):
    async def event_source():
        async for event in stream_message(
            container.graph, payload.session_id, payload.message, auth
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@chat_router.get("/{session_id}")
async def get_chat_history(
    session_id: UUID,
    container: AppContainer = Depends(get_container),
):
    history = await get_history(container.graph, session_id)
    return success(
        data={
            "session_id": str(history.session_id),
            "messages": [{"role": t.role, "content": t.content} for t in history.turns],
        }
    )
