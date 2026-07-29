"""Cross-cutting Audit Logging Utility for System & Admin Actions."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

logger = logging.getLogger(__name__)


class AuditLogModel(Base):
    """SQLAlchemy ORM Model representing system audit log entries.

    Tracks actions performed across the application by users or background processes.
    """

    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(50), nullable=False)
    resource_id = Column(PG_UUID(as_uuid=True), nullable=True)
    payload = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


async def log_audit_event(
    session: AsyncSession,
    user_id: Optional[UUID],
    action: str,
    resource: str,
    resource_id: Optional[UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Record an action entry into the audit_logs database table.

    Executes within the active database AsyncSession to maintain transaction atomicity.
    Catches any internal exceptions locally to prevent audit logging failure from aborting
    the primary business operation.

    Args:
        session (AsyncSession): Active database session shared with the request transaction.
        user_id (Optional[UUID]): Unique identifier of the user performing the action (None for system events).
        action (str): Event identifier string (e.g. 'order.status_changed', 'user.login').
        resource (str): Target resource domain name (e.g. 'orders', 'users').
        resource_id (Optional[UUID]): Target entity primary key UUID.
        payload (Optional[Dict[str, Any]]): Contextual metadata or payload payload.
        ip_address (Optional[str]): Client IP address extracted from the HTTP request.
    """
    try:
        audit_entry = AuditLogModel(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            payload=payload,
            ip_address=ip_address,
        )
        session.add(audit_entry)
    except Exception as err:
        logger.error(f"Failed to record audit log event [{action}] on [{resource}]: {err}")
