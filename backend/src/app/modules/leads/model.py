"""SQLAlchemy ORM Models for the Leads Module.

Defines database mapping for LeadModel.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.database import Base


class LeadModel(Base):
    """SQLAlchemy ORM Model representing customer leads / test drive inquiries."""

    __tablename__ = "leads"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(PG_UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    showroom_pref = Column(String(100), nullable=True)
    status = Column(String(50), default="new", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
