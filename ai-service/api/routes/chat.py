"""Chat router: one endpoint driving the supervisor agent."""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from loguru import logger

from api.response import success
from api.schemas import ChatRequestSchema, ChatResponseSchema

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.post("")
async def chat(payload: ChatRequestSchema, request: Request) -> JSONResponse:
    """Run one chat turn against the supervisor agent.

    Reuses the thread when thread_id is provided, otherwise starts a new
    conversation and returns the generated thread_id for follow-ups.
    """
    supervisor = request.app.state.supervisor
    thread_id = payload.thread_id or f"web-{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    logger.info("Chat turn started [thread_id={}, message_len={}]", thread_id, len(payload.message))
    result = await supervisor.ainvoke(
        {"messages": [HumanMessage(content=payload.message)]}, config
    )

    reply = result["messages"][-1].content
    if not isinstance(reply, str):
        reply = str(reply)
    logger.info("Chat turn done [thread_id={}, reply_len={}]", thread_id, len(reply))

    data = ChatResponseSchema(thread_id=thread_id, reply=reply)
    return success(data=data.model_dump())
