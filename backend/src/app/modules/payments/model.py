"""SQLAlchemy ORM Models for the Payments Module.

Defines database mapping for PaymentModel.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.database import Base


class PaymentModel(Base):
    """SQLAlchemy ORM Model representing payment transactions."""

    __tablename__ = "payments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method = Column(String(50), default="vnpay", nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)
    transaction_code = Column(String(100), nullable=True, index=True)
    payment_url = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
