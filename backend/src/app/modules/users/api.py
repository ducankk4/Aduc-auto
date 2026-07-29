"""FastAPI Presentation Layer Routers for the Users Module."""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import check_permission, get_current_user
from app.core.response import success
from app.modules.users.schema import (
    CreateRoleRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.modules.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
admin_users_router = APIRouter(prefix="/admin/users", tags=["Admin Users Management"])


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """Register a new customer account."""
    user = await UserService.register(
        session=session,
        username=req.username,
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        phone=req.phone,
    )
    user_response = await UserService.get_user_profile(session, user.id)
    return success(data=user_response.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate credentials and receive JWT Access & Refresh Tokens."""
    token_response = await UserService.login(
        session=session,
        username_or_email=req.username_or_email,
        password=req.password,
    )
    return success(data=token_response.model_dump(mode="json"))


@auth_router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    req: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """Obtain a new Access Token using a valid Refresh Token."""
    token_response = await UserService.refresh_token(
        session=session,
        refresh_token_str=req.refresh_token,
    )
    return success(data=token_response.model_dump(mode="json"))


@auth_router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetch profile information for the authenticated user."""
    user_id = UUID(current_user["sub"])
    user_profile = await UserService.get_user_profile(session, user_id)
    return success(data=user_profile.model_dump(mode="json"))


@admin_users_router.get("", dependencies=[Depends(check_permission("users", "manage"))])
async def list_users(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """Admin Endpoint: List users with pagination."""
    users, total = await UserService.list_users(session, page=page, limit=limit)
    data = [u.model_dump(mode="json") for u in users]
    return success(data=data, meta={"page": page, "limit": limit, "total": total})


@admin_users_router.get("/departments", dependencies=[Depends(check_permission("users", "manage"))])
async def get_departments(
    session: AsyncSession = Depends(get_db),
):
    """Admin Endpoint: List all company departments / showroom branches."""
    departments = await UserService.get_departments(session)
    data = [d.model_dump(mode="json") for d in departments]
    return success(data=data)


@admin_users_router.get("/roles", dependencies=[Depends(check_permission("roles", "manage"))])
async def get_roles(
    session: AsyncSession = Depends(get_db),
):
    """Admin Endpoint: List all roles and assigned permission keys."""
    roles = await UserService.get_roles(session)
    data = [r.model_dump(mode="json") for r in roles]
    return success(data=data)


@admin_users_router.post("/roles", status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_permission("roles", "manage"))])
async def create_role(
    req: CreateRoleRequest,
    session: AsyncSession = Depends(get_db),
):
    """Admin Endpoint: Create a new role."""
    role = await UserService.create_role(session, name=req.name, description=req.description)
    return success(data=role.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)
