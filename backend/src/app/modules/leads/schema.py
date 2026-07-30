"""Pydantic Schemas (DTOs) for the Leads Module."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.leads.constants import LeadStatus


class LeadCreateSchema(BaseModel):
    """Schema for public lead submission request."""

    vehicle_id: UUID
    customer_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=8, max_length=20)
    email: EmailStr
    showroom_pref: Optional[str] = Field(None, max_length=100)


class LeadStatusUpdateSchema(BaseModel):
    """Schema for admin updating lead status."""

    status: LeadStatus


class LeadResponseSchema(BaseModel):
    """Schema for returning lead information."""

    id: UUID
    vehicle_id: UUID
    customer_name: str
    phone: str
    email: str
    showroom_pref: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
