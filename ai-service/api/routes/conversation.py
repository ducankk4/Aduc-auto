"""Conversation router: read back stored chat history."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.response import success
from api.schemas.conversation import ConversationResponse, SessionResponse

conversation_router = APIRouter(prefix="/conversation", tags=["Conversation"])


@conversation_router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request) -> JSONResponse:
    message_service = request.app.state.message_service
    sessions = await message_service.get_recent_sessions(conversation_id)

    data = ConversationResponse(
        conversation_id=conversation_id,
        sessions=[SessionResponse.from_domain(session) for session in sessions],
    )
    return success(data=data.model_dump(mode="json"))
