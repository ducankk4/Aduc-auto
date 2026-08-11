"""FastAPI dependencies: extract the Bearer token and build an AuthContext.

Only decodes the JWT payload to read `role`/`permissions` for UI-level
subagent visibility — the signature is never verified here. Backend is the
sole RBAC authority (CLAUDE.md invariant #3); this decode is never used to
grant access, so plain stdlib base64/json is enough — no JWT library needed.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ai_service.domain.actor import AuthContext

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthContext:
    if not credentials or not credentials.credentials:
        return AuthContext.anonymous()

    token = credentials.credentials
    claims = _decode_unverified_claims(token)
    return AuthContext(
        token=token,
        is_authenticated=True,
        role=claims.get("role"),
        permissions=list(claims.get("permissions") or []),
    )


def _decode_unverified_claims(token: str) -> dict[str, Any]:
    """Decode a JWT payload segment without verifying its signature.

    A malformed token yields an empty dict rather than raising — the caller
    only uses this for UI-level subagent visibility, never for authorization
    decisions, so decode failure degrades to "no known role/permissions".
    """
    try:
        _, payload_b64, _ = token.split(".")
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded)
        return json.loads(payload_bytes)
    except (ValueError, json.JSONDecodeError):
        return {}
