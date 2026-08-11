"""Runtime context passed into the supervisor graph per-request.

This is LangGraph's `context` channel, which is never part of `AgentState`
and therefore never persisted by the checkpointer — this is what keeps the
Bearer token out of the conversation store (CLAUDE.md invariant #7).
"""

from __future__ import annotations

from typing import TypedDict


class AgentContext(TypedDict, total=False):
    auth_token: str | None
