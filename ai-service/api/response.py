"""Standardized API response wrappers — same envelope as the backend."""

from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse


def success(data: Any, meta: Optional[Dict[str, Any]] = None, status_code: int = 200) -> JSONResponse:
    """Build a standardized success response: {"success": true, "data": ...}."""
    content: Dict[str, Any] = {"success": True, "data": data}
    if meta is not None:
        content["meta"] = meta
    return JSONResponse(content=content, status_code=status_code)


def error(code: str, message: str, status_code: int = 400) -> JSONResponse:
    """Build a standardized error response: {"success": false, "error": {...}}."""
    return JSONResponse(
        content={"success": False, "error": {"code": code, "message": message}},
        status_code=status_code,
    )
