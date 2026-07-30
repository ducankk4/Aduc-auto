"""Pydantic Schemas (DTOs) for the Payments Module."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PaymentInitResponseSchema(BaseModel):
    """Schema for payment initialization response."""

    payment_id: UUID
    order_id: UUID
    order_code: str
    amount: Decimal
    payment_url: str


class PaymentResponseSchema(BaseModel):
    """Schema for payment details."""

    id: UUID
    order_id: UUID
    payment_method: str
    amount: Decimal
    status: str
    transaction_code: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
