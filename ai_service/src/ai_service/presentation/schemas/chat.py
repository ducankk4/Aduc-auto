"""Request/response DTOs for the /chat endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    content: str
