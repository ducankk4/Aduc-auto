"""Reusable FastAPI Dependencies: Authentication & Fine-Grained Permission Enforcement."""

from typing import Any, Callable, Dict, Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Validate Bearer JWT Token and return the decoded token payload.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): Bearer token extracted from HTTP Header.
        session (AsyncSession): Active database session injected via get_db dependency.

    Returns:
        Dict[str, Any]: Decoded JWT token payload dictionary containing user attributes.

    Raises:
        UnauthorizedError: If Bearer token is missing, invalid, expired, or wrong type.
    """
    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Chưa đăng nhập hoặc thiếu Bearer Token")

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedError("Token không phải là Access Token hợp lệ")
        return payload
    except Exception as err:
        raise UnauthorizedError("Token không hợp lệ hoặc đã hết hạn") from err


def check_permission(resource: str, action: str) -> Callable:
    """FastAPI Dependency Factory for fine-grained Permission Checking.

    Usage:
    ```python
    @router.get("/admin/orders", dependencies=[Depends(check_permission("orders", "read"))])
    ```

    Args:
        resource (str): Target domain resource (e.g. 'orders', 'catalog').
        action (str): Specific action descriptor (e.g. 'read', 'create', 'update_status').

    Returns:
        Callable: FastAPI dependency enforcing role and resource permission rules.
    """
    async def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "")
        if user_role == "admin":
            return current_user

        user_permissions = current_user.get("permissions", [])
        required_perm = f"{resource}:{action}"
        if required_perm not in user_permissions:
            raise ForbiddenError(f"Tài khoản không có quyền [{required_perm}] để thực hiện thao tác này")

        return current_user

    return permission_checker
