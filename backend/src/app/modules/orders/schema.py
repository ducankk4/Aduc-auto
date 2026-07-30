"""Pydantic Schemas (DTOs) for the Orders Module."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.orders.constants import OrderStatus


class OrderCreateSchema(BaseModel):
    """Schema for customer creating a car deposit order."""

    variant_id: UUID
    color_id: UUID
    customer_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=8, max_length=20)
    email: EmailStr
    id_card: str = Field(..., min_length=6, max_length=50)


class OrderUpdateStatusSchema(BaseModel):
    """Schema for admin updating order lifecycle status."""

    status: OrderStatus
    note: Optional[str] = Field(None, max_length=500)


class OrderStatusHistorySchema(BaseModel):
    """Schema for returning order status history entries."""

    id: UUID
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[UUID] = None
    changed_at: datetime
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponseSchema(BaseModel):
    """Schema for returning order details."""

    id: UUID
    order_code: str
    user_id: Optional[UUID] = None
    variant_id: UUID
    color_id: UUID
    deposit_amount: Decimal
    status: str
    customer_name: str
    phone: str
    email: str
    id_card: str
    created_at: datetime
    history: List[OrderStatusHistorySchema] = []

    model_config = ConfigDict(from_attributes=True)
