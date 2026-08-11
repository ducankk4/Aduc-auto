"""Response envelope helper — mirrors backend/src/app/core/response.py's
{success, data, meta} shape so the frontend can reuse one response parser
for both services.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def success(data: Any, meta: dict[str, Any] | None = None, status_code: int = 200) -> JSONResponse:
    content: dict[str, Any] = {"success": True, "data": data}
    if meta is not None:
        content["meta"] = meta
    return JSONResponse(content=content, status_code=status_code)
