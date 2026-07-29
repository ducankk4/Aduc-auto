"""Business Logic and Public Interface Service Layer for the Users Module."""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.modules.users.constants import DefaultRole
from app.modules.users.model import RoleModel, UserModel
from app.modules.users.repository import UserRepository
from app.modules.users.schema import (
    DepartmentResponse,
    RoleResponse,
    TokenResponse,
    UserResponse,
)


class UserService:
    """Provides business logic workflows and public interfaces for user management and authentication."""

    @staticmethod
    async def register(
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
        full_name: str,
        phone: str,
    ) -> UserModel:
        """Register a new customer account into the platform.

        Args:
            session (AsyncSession): Active database session.
            username (str): Desired login username.
            email (str): Registered email address.
            password (str): Plaintext password to be hashed.
            full_name (str): Full name of the user.
            phone (str): Contact phone number.

        Returns:
            UserModel: Newly created user database model entity.

        Raises:
            ConflictError: If username or email is already registered.
        """
        # Validate email uniqueness
        existing_email = await UserRepository.get_by_email(session, email)
        if existing_email:
            raise ConflictError("Email này đã được đăng ký trên hệ thống")

        # Validate username uniqueness
        existing_username = await UserRepository.get_by_username(session, username)
        if existing_username:
            raise ConflictError("Tên đăng nhập này đã tồn tại")

        # Ensure default customer role exists
        customer_role = await UserRepository.get_role_by_name(session, DefaultRole.CUSTOMER.value)
        if not customer_role:
            customer_role = RoleModel(
                name=DefaultRole.CUSTOMER.value,
                description="Khách hàng đăng ký tài khoản đặt cọc xe",
            )
            customer_role = await UserRepository.create_role(session, customer_role)

        # Hash password and instantiate UserModel
        hashed_pwd = hash_password(password)
        new_user = UserModel(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=hashed_pwd,
            full_name=full_name.strip(),
            phone=phone.strip(),
            is_active=True,
            role_id=customer_role.id,
        )

        return await UserRepository.create(session, new_user)

    @staticmethod
    async def login(
        session: AsyncSession,
        username_or_email: str,
        password: str,
    ) -> TokenResponse:
        """Authenticate user credentials and issue JWT Access and Refresh tokens.

        Args:
            session (AsyncSession): Active database session.
            username_or_email (str): Username or email string.
            password (str): Plaintext password to verify.

        Returns:
            TokenResponse: Object containing access_token, refresh_token, and expiration.

        Raises:
            UnauthorizedError: If credentials are invalid or account is deactivated.
        """
        target = username_or_email.strip()
        user = await UserRepository.get_by_email(session, target)
        if not user:
            user = await UserRepository.get_by_username(session, target)

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Tên đăng nhập hoặc mật khẩu không chính xác")

        if not user.is_active:
            raise UnauthorizedError("Tài khoản của bạn hiện đang bị tạm khóa")

        # Fetch permissions assigned to user role
        permissions = await UserRepository.get_permissions_for_user(session, user.id)

        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.name if user.role else DefaultRole.CUSTOMER.value,
            "permissions": permissions,
        }

        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def refresh_token(
        session: AsyncSession,
        refresh_token_str: str,
    ) -> TokenResponse:
        """Issue a new JWT access token using a valid refresh token.

        Args:
            session (AsyncSession): Active database session.
            refresh_token_str (str): Provided refresh token string.

        Returns:
            TokenResponse: New access token and refresh token pair.

        Raises:
            UnauthorizedError: If refresh token is invalid, expired, or wrong type.
        """
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise UnauthorizedError("Token không phải là Refresh Token hợp lệ")

            user_id_str = payload.get("sub")
            if not user_id_str:
                raise UnauthorizedError("Payload token không hợp lệ")

            user_id = UUID(user_id_str)
        except Exception as err:
            raise UnauthorizedError("Refresh Token không hợp lệ hoặc đã hết hạn") from err

        user = await UserRepository.get_by_id(session, user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("Tài khoản không tồn tại hoặc đã bị khóa")

        permissions = await UserRepository.get_permissions_for_user(session, user.id)
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.name if user.role else DefaultRole.CUSTOMER.value,
            "permissions": permissions,
        }

        new_access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def check_permission(
        session: AsyncSession,
        user_id: UUID,
        resource: str,
        action: str,
    ) -> bool:
        """Public Service Interface: Check if a user possesses a specific resource:action permission.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): User primary key UUID.
            resource (str): Target domain resource string (e.g. 'orders', 'catalog').
            action (str): Target action permission (e.g. 'read', 'update_status').

        Returns:
            bool: True if permission is granted, False otherwise.
        """
        user = await UserRepository.get_by_id(session, user_id)
        if not user or not user.is_active:
            return False

        if user.role and user.role.name == DefaultRole.ADMIN.value:
            return True

        permissions = await UserRepository.get_permissions_for_user(session, user_id)
        required_perm = f"{resource}:{action}"
        return required_perm in permissions

    @staticmethod
    async def get_user_profile(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserResponse:
        """Fetch UserResponse object for a specific user ID.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): Target user ID.

        Returns:
            UserResponse: User profile DTO without sensitive fields.

        Raises:
            NotFoundError: If user entity is not found.
        """
        user = await UserRepository.get_by_id(session, user_id)
        if not user:
            raise NotFoundError("Người dùng không tồn tại trên hệ thống")

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            is_active=user.is_active,
            role_name=user.role.name if user.role else DefaultRole.CUSTOMER.value,
            department_id=user.department_id,
            created_at=user.created_at,
        )

    @staticmethod
    async def list_users(
        session: AsyncSession,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[list[UserResponse], int]:
        """Fetch a paginated list of user responses for admin management.

        Args:
            session (AsyncSession): Active database session.
            page (int): Current page number (1-indexed).
            limit (int): Items per page.

        Returns:
            Tuple[list[UserResponse], int]: Tuple containing user DTO list and total record count.
        """
        offset = (page - 1) * limit
        users, total = await UserRepository.list_users(session, limit=limit, offset=offset)

        user_responses = [
            UserResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                phone=u.phone,
                is_active=u.is_active,
                role_name=u.role.name if u.role else DefaultRole.CUSTOMER.value,
                department_id=u.department_id,
                created_at=u.created_at,
            )
            for u in users
        ]
        return user_responses, total

    @staticmethod
    async def get_departments(session: AsyncSession) -> list[DepartmentResponse]:
        """Fetch all company departments / showroom branches.

        Args:
            session (AsyncSession): Active database session.

        Returns:
            list[DepartmentResponse]: Department DTO list.
        """
        departments = await UserRepository.get_departments(session)
        return [DepartmentResponse.model_validate(d) for d in departments]

    @staticmethod
    async def get_roles(session: AsyncSession) -> list[RoleResponse]:
        """Fetch all system roles.

        Args:
            session (AsyncSession): Active database session.

        Returns:
            list[RoleResponse]: Role DTO list.
        """
        roles = await UserRepository.get_roles(session)
        responses = []
        for role in roles:
            perm_strings = [f"{p.resource}:{p.action}" for p in role.permissions]
            responses.append(
                RoleResponse(
                    id=role.id,
                    name=role.name,
                    description=role.description,
                    permissions=perm_strings,
                )
            )
        return responses

    @staticmethod
    async def create_role(
        session: AsyncSession,
        name: str,
        description: Optional[str] = None,
    ) -> RoleResponse:
        """Create a new role entity in the database.

        Args:
            session (AsyncSession): Active database session.
            name (str): Unique role name string.
            description (Optional[str]): Optional role description.

        Returns:
            RoleResponse: Created role DTO.

        Raises:
            ConflictError: If role name already exists.
        """
        existing = await UserRepository.get_role_by_name(session, name)
        if existing:
            raise ConflictError(f"Vai trò [{name}] đã tồn tại trong hệ thống")

        new_role = RoleModel(name=name.strip().lower(), description=description)
        created = await UserRepository.create_role(session, new_role)
        return RoleResponse(id=created.id, name=created.name, description=created.description, permissions=[])
