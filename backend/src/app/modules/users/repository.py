"""Data Access Layer for the Users Module (Pure SQLAlchemy Queries)."""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.users.model import DepartmentModel, PermissionModel, RoleModel, UserModel, role_permissions


class UserRepository:
    """Encapsulates all database operations for user management, roles, and permissions."""

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Optional[UserModel]:
        """Fetch a single user by their email address.

        Args:
            session (AsyncSession): Active database session.
            email (str): Target email string.

        Returns:
            Optional[UserModel]: Found user entity or None.
        """
        stmt = select(UserModel).where(UserModel.email == email.strip().lower())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> Optional[UserModel]:
        """Fetch a single user by their unique username.

        Args:
            session (AsyncSession): Active database session.
            username (str): Target username string.

        Returns:
            Optional[UserModel]: Found user entity or None.
        """
        stmt = select(UserModel).where(UserModel.username == username.strip())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: UUID) -> Optional[UserModel]:
        """Fetch a user entity by their primary key UUID.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): Primary key UUID.

        Returns:
            Optional[UserModel]: Found user entity or None.
        """
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, user: UserModel) -> UserModel:
        """Persist a new UserModel instance into the database session.

        Args:
            session (AsyncSession): Active database session.
            user (UserModel): Unpersisted user model instance.

        Returns:
            UserModel: Persisted user model instance.
        """
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def get_role_by_name(session: AsyncSession, name: str) -> Optional[RoleModel]:
        """Retrieve a role entity by its unique name string.

        Args:
            session (AsyncSession): Active database session.
            name (str): Unique role name (e.g. 'admin', 'customer').

        Returns:
            Optional[RoleModel]: Role entity or None.
        """
        stmt = select(RoleModel).where(RoleModel.name == name.strip().lower())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_permissions_for_user(session: AsyncSession, user_id: UUID) -> list[str]:
        """Fetch all permission keys (formatted as 'resource:action') assigned to a user.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): User primary key UUID.

        Returns:
            list[str]: List of permission strings.
        """
        stmt = (
            select(PermissionModel.resource, PermissionModel.action)
            .join(role_permissions, PermissionModel.id == role_permissions.c.permission_id)
            .join(UserModel, UserModel.role_id == role_permissions.c.role_id)
            .where(UserModel.id == user_id)
        )
        result = await session.execute(stmt)
        rows = result.all()
        return [f"{row.resource}:{row.action}" for row in rows]

    @staticmethod
    async def list_users(session: AsyncSession, limit: int = 10, offset: int = 0) -> Tuple[list[UserModel], int]:
        """Fetch a paginated list of user records and total count.

        Args:
            session (AsyncSession): Active database session.
            limit (int): Pagination size.
            offset (int): Pagination offset.

        Returns:
            Tuple[list[UserModel], int]: Tuple containing the list of user records and total record count.
        """
        count_stmt = select(func.count(UserModel.id))
        total = (await session.execute(count_stmt)).scalar_one()

        query_stmt = select(UserModel).order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
        users = (await session.execute(query_stmt)).scalars().all()
        return list(users), total

    @staticmethod
    async def get_departments(session: AsyncSession) -> list[DepartmentModel]:
        """Fetch all company departments or showroom branches.

        Args:
            session (AsyncSession): Active database session.

        Returns:
            list[DepartmentModel]: List of all department entities.
        """
        stmt = select(DepartmentModel).options(selectinload(DepartmentModel.children))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_roles(session: AsyncSession) -> list[RoleModel]:
        """Fetch all system roles.

        Args:
            session (AsyncSession): Active database session.

        Returns:
            list[RoleModel]: List of all system roles.
        """
        stmt = select(RoleModel).options(selectinload(RoleModel.permissions))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_role(session: AsyncSession, role: RoleModel) -> RoleModel:
        """Persist a new RoleModel instance into the database session.

        Args:
            session (AsyncSession): Active database session.
            role (RoleModel): Unpersisted role model instance.

        Returns:
            RoleModel: Persisted role entity.
        """
        session.add(role)
        await session.flush()
        return role
