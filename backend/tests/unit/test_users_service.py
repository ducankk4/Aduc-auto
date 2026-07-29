"""Unit Tests for Users Service (Register, Login, Check Permission)."""

from unittest.mock import AsyncMock, patch
import pytest
from app.core.exceptions import ConflictError, UnauthorizedError
from app.modules.users.model import RoleModel, UserModel
from app.modules.users.service import UserService


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_conflict():
    """Verify that registering with an already existing email raises ConflictError (409)."""
    mock_session = AsyncMock()
    existing_user = UserModel(username="user1", email="test@example.com")

    with patch("app.modules.users.repository.UserRepository.get_by_email", return_value=existing_user):
        with pytest.raises(ConflictError) as exc_info:
            await UserService.register(
                session=mock_session,
                username="newuser",
                email="test@example.com",
                password="Password123!",
                full_name="Test User",
                phone="0987654321",
            )
        assert "Email này đã được đăng ký" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_login_invalid_password_raises_unauthorized():
    """Verify that login with incorrect password raises UnauthorizedError (401)."""
    mock_session = AsyncMock()
    mock_role = RoleModel(name="customer")
    existing_user = UserModel(
        username="user1",
        email="test@example.com",
        password_hash="$2b$12$e868N...",
        is_active=True,
        role=mock_role,
    )

    with patch("app.modules.users.repository.UserRepository.get_by_email", return_value=existing_user):
        with patch("app.modules.users.service.verify_password", return_value=False):
            with pytest.raises(UnauthorizedError) as exc_info:
                await UserService.login(
                    session=mock_session,
                    username_or_email="test@example.com",
                    password="WrongPassword!",
                )
            assert "không chính xác" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_check_permission_granted_and_denied():
    """Verify that check_permission returns True for granted permissions and False otherwise."""
    mock_session = AsyncMock()
    user_id = UserModel().id

    # Admin user gets True automatically
    admin_user = UserModel(id=user_id, is_active=True, role=RoleModel(name="admin"))
    with patch("app.modules.users.repository.UserRepository.get_by_id", return_value=admin_user):
        has_perm = await UserService.check_permission(mock_session, user_id, "orders", "cancel")
        assert has_perm is True

    # Regular user check
    regular_user = UserModel(id=user_id, is_active=True, role=RoleModel(name="customer"))
    with patch("app.modules.users.repository.UserRepository.get_by_id", return_value=regular_user):
        with patch("app.modules.users.repository.UserRepository.get_permissions_for_user", return_value=["orders:read_own"]):
            # Granted
            assert await UserService.check_permission(mock_session, user_id, "orders", "read_own") is True
            # Denied
            assert await UserService.check_permission(mock_session, user_id, "orders", "delete") is False
