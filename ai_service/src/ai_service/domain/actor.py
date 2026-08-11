"""Authentication context for the current request actor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthContext:
    """Decoded (but signature-unverified) view of the caller's Bearer token.

    Used only to show/hide subagents in the UI and to pass the raw token
    through to backend calls. Backend remains the sole authority on RBAC
    (CLAUDE.md invariant #3) — nothing here is ever used to grant access.
    """

    token: str | None
    is_authenticated: bool
    role: str | None = None
    permissions: list[str] = field(default_factory=list)

    @classmethod
    def anonymous(cls) -> "AuthContext":
        return cls(token=None, is_authenticated=False, role=None, permissions=[])

