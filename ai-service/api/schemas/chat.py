"""Pydantic Schemas (DTOs) for the chat API."""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema for one chat turn sent by the client."""

    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Gửi lại conversation_id nhận được ở lượt trước để tiếp tục hội thoại; bỏ trống để mở hội thoại mới.",
    )
    user_id: Optional[str] = Field(None, max_length=64)


class ChatResponse(BaseModel):
    """Schema for the assistant reply of one chat turn."""

    conversation_id: str
    session_id: str
    reply: str
