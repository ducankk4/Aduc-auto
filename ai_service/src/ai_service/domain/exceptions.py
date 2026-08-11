"""Base exception hierarchy for ai-service, mapped to HTTP responses at the
presentation boundary (see bootstrap/app_factory.py).
"""

from __future__ import annotations

from typing import Any


class AiServiceError(Exception):
    """Base for every ai-service domain/application exception.

    Subclasses set `code` (stable machine-readable identifier) and
    `status_code` (HTTP status mapped at the presentation boundary).
    `message` is client-facing text, following the same {success,error}
    envelope shape used by `backend`.
    """

    code: str = "AI_SERVICE_ERROR"
    status_code: int = 500

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ConversationNotFoundError(AiServiceError):
    code = "CONVERSATION_NOT_FOUND"
    status_code = 404
