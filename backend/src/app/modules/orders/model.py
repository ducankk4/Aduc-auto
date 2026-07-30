"""SQLAlchemy ORM Models for the Orders Module.

Defines database mapping for OrderModel and OrderStatusHistory.
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
from sqlalchemy.orm import relationship

from app.core.database import Base


class OrderModel(Base):
    """SQLAlchemy ORM Model representing car deposit orders."""

    __tablename__ = "orders"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_code = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_id = Column(PG_UUID(as_uuid=True), ForeignKey("vehicle_variants.id", ondelete="RESTRICT"), nullable=False)
    color_id = Column(PG_UUID(as_uuid=True), ForeignKey("vehicle_colors.id", ondelete="RESTRICT"), nullable=False)
    deposit_amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)

    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    id_card = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.changed_at.asc()",
    )


class OrderStatusHistory(Base):
    """SQLAlchemy ORM Model representing order status change history trail."""

    __tablename__ = "order_status_history"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    note = Column(Text, nullable=True)

    order = relationship("OrderModel", back_populates="history")
