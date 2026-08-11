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
