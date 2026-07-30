"""Pydantic Schemas (DTOs) for the Catalog Module."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class VariantCreateSchema(BaseModel):
    """Schema for creating a vehicle variant."""

    name: str = Field(..., max_length=100)
    sku: str = Field(..., max_length=50)
    price: Decimal = Field(..., gt=0)
    specs: Optional[Dict[str, Any]] = None


class VariantResponseSchema(BaseModel):
    """Schema for returning variant details."""

    id: UUID
    vehicle_id: UUID
    name: str
    sku: str
    price: Decimal
    specs: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ColorCreateSchema(BaseModel):
    """Schema for creating a vehicle color option."""

    name: str = Field(..., max_length=50)
    color_code: str = Field(..., max_length=20)
    price_extra: Decimal = Field(default=Decimal("0.00"), ge=0)


class ColorResponseSchema(BaseModel):
    """Schema for returning color details."""

    id: UUID
    vehicle_id: UUID
    name: str
    color_code: str
    price_extra: Decimal

    model_config = ConfigDict(from_attributes=True)


class OptionResponseSchema(BaseModel):
    """Schema for returning optional add-on equipment."""

    id: UUID
    vehicle_id: UUID
    name: str
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class VehicleCreateSchema(BaseModel):
    """Schema for admin vehicle creation request."""

    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=120)
    category: str = Field(..., max_length=50)
    description: Optional[str] = None
    base_price: Decimal = Field(..., gt=0)
    is_active: bool = True
    variants: List[VariantCreateSchema] = []
    colors: List[ColorCreateSchema] = []


class VehicleUpdateSchema(BaseModel):
    """Schema for admin vehicle update request."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None


class VehicleResponseSchema(BaseModel):
    """Schema for vehicle details in public/admin API responses."""

    id: UUID
    name: str
    slug: str
    category: str
    description: Optional[str] = None
    base_price: Decimal
    is_active: bool
    created_at: datetime
    variants: List[VariantResponseSchema] = []
    colors: List[ColorResponseSchema] = []

    model_config = ConfigDict(from_attributes=True)
