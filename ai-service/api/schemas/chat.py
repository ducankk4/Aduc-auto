"""Pydantic Schemas (DTOs) for the chat API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Gửi lại conversation_id nhận được ở lượt trước để tiếp tục hội thoại; bỏ trống để mở hội thoại mới.",
    )
    user_id: Optional[str] = Field(None, max_length=64)


class ApprovalRequest(BaseModel):
    """One sensitive tool call awaiting human review."""

    tool: str
    args: Dict[str, Any]
    allowed_decisions: List[str]


class ChatResponse(BaseModel):
    conversation_id: str
    session_id: str
    interrupted: bool = False
    reply: Optional[str] = None
    approval_requests: List[ApprovalRequest] = Field(default_factory=list)


class ResumeDecision(BaseModel):
    type: Literal["approve", "edit", "reject"]
    tool: Optional[str] = Field(None, description="Tên tool — bắt buộc khi type là edit.")
    args: Optional[Dict[str, Any]] = Field(
        None, description="Tham số mới cho tool — bắt buộc khi type là edit."
    )
    message: Optional[str] = Field(
        None, max_length=500, description="Lý do từ chối (tùy chọn, chỉ dùng với reject)."
    )

    @model_validator(mode="after")
    def _require_edit_fields(self) -> "ResumeDecision":
        """Reject an edit decision that carries no edited action."""
        if self.type == "edit" and (self.tool is None or self.args is None):
            raise ValueError("Quyết định 'edit' phải kèm cả tool lẫn args.")
        return self


class ResumeRequest(BaseModel):
    """Schema for resuming a turn halted by an approval request."""

    conversation_id: str = Field(..., max_length=64)
    session_id: str = Field(
        ...,
        max_length=64,
        description="session_id của đúng lượt bị dừng — resume lượt khác sẽ không có gì để tiếp tục.",
    )
    decisions: List[ResumeDecision] = Field(..., min_length=1)
