"""Pydantic Request & Response Schemas (DTOs) for the Users Module."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Data transfer object for customer user registration."""

    username: str = Field(..., min_length=3, max_length=50, description="Unique login username")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, description="Account password (minimum 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    phone: str = Field(..., min_length=10, max_length=20, description="Contact phone number")


class LoginRequest(BaseModel):
    """Data transfer object for user authentication login."""

    username_or_email: str = Field(..., description="Username or registered email address")
    password: str = Field(..., description="Account password")


class RefreshTokenRequest(BaseModel):
    """Data transfer object for refreshing JWT access tokens."""

    refresh_token: str = Field(..., description="Valid JWT Refresh Token")


class TokenResponse(BaseModel):
    """Data transfer object returned upon successful login or refresh."""

    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Token authentication scheme")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class PermissionSchema(BaseModel):
    """DTO representing granular permissions."""

    id: UUID
    resource: str
    action: str

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    """DTO representing a user role."""

    id: UUID
    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list, description="Assigned permission strings")

    model_config = ConfigDict(from_attributes=True)


class CreateRoleRequest(BaseModel):
    """DTO for creating a new role."""

    name: str = Field(..., min_length=2, max_length=50, description="Role name")
    description: Optional[str] = Field(None, description="Optional role description")


class DepartmentResponse(BaseModel):
    """DTO representing a company department or showroom branch."""

    id: UUID
    name: str
    parent_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """DTO for user profile output. Explicitly excludes password_hash for security."""

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    phone: str
    is_active: bool
    role_name: str = Field(..., description="Associated role name string")
    department_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
