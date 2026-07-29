"""SQLAlchemy ORM Models for the Users Module.

Defines database mapping for UserModel, RoleModel, PermissionModel, DepartmentModel,
and the role_permissions association table.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

# Association Table for Many-to-Many relationship between Roles and Permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", PG_UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class PermissionModel(Base):
    """SQLAlchemy ORM Model for Granular Resource Permissions."""

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permission_resource_action"),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)

    roles = relationship("RoleModel", secondary=role_permissions, back_populates="permissions")


class RoleModel(Base):
    """SQLAlchemy ORM Model for User System Roles."""

    __tablename__ = "roles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    users = relationship("UserModel", back_populates="role")
    permissions = relationship("PermissionModel", secondary=role_permissions, back_populates="roles")


class DepartmentModel(Base):
    """SQLAlchemy ORM Model for Company Departments / Showroom Branches."""

    __tablename__ = "departments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    parent = relationship("DepartmentModel", remote_side=[id], backref="children")
    users = relationship("UserModel", back_populates="department")


class UserModel(Base):
    """SQLAlchemy ORM Model for Registered Accounts."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role_id = Column(PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    department_id = Column(PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    role = relationship("RoleModel", back_populates="users", lazy="joined")
    department = relationship("DepartmentModel", back_populates="users", lazy="joined")
