"""Standardized API Response Wrappers."""

from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success(data: Any, meta: Optional[Dict[str, Any]] = None, status_code: int = 200) -> JSONResponse:
    """Build a Standardized Success Response.

    Format:
    {
        "success": true,
        "data": ...,
        "meta": { "page": 1, "limit": 12, "total": 50 }  # Optional
    }
    """
    content: Dict[str, Any] = {"success": True, "data": data}
    if meta is not None:
        content["meta"] = meta
    return JSONResponse(content=content, status_code=status_code)


def error(code: str, message: str, status_code: int = 400) -> JSONResponse:
    """Build a Standardized Error Response.

    Format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Chi tiết lỗi"
        }
    }
    """
    content = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    return JSONResponse(content=content, status_code=status_code)
