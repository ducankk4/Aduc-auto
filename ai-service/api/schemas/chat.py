"""Pydantic Schemas (DTOs) for the chat API."""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequestSchema(BaseModel):
    """Schema for one chat turn sent by the client."""

    message: str = Field(..., min_length=1, max_length=4000)
    thread_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Gửi lại thread_id nhận được ở lượt trước để tiếp tục hội thoại; bỏ trống để mở hội thoại mới.",
    )


class ChatResponseSchema(BaseModel):
    """Schema for the assistant reply of one chat turn."""

    thread_id: str
    reply: str
