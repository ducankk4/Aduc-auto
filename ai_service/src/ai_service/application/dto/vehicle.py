"""DTOs describing catalog data as it crosses application layer boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class VehicleSummaryDTO:
    id: UUID
    name: str
    slug: str
    category: str
    base_price: Decimal
    is_active: bool


@dataclass(frozen=True)
class VariantDTO:
    id: UUID
    name: str
    sku: str
    price: Decimal


@dataclass(frozen=True)
class ColorDTO:
    id: UUID
    name: str
    color_code: str
    price_extra: Decimal


@dataclass(frozen=True)
class VehicleDetailDTO:
    id: UUID
    name: str
    slug: str
    category: str
    description: str | None
    base_price: Decimal
    is_active: bool
    variants: list[VariantDTO]
    colors: list[ColorDTO]
