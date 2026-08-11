"""DTOs describing chat use case results."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ChatResultDTO:
    session_id: UUID
    reply: str
