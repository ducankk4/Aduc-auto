"""Vehicle domain entities shared across ai-service.

Pure Python only — mirrors the business shape of the backend catalog,
not its API or DB schema.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from uuid import UUID


@dataclass(frozen=True)
class CarVariant:
    """A purchasable variant (trim) of a vehicle."""

    id: UUID
    name: str
    sku: str
    price: Decimal


@dataclass(frozen=True)
class CarColor:
    """An exterior color option of a vehicle."""

    id: UUID
    name: str
    color_code: str
    price_extra: Decimal


@dataclass(frozen=True)
class Car:
    """A vehicle offered in the catalog."""

    id: UUID
    name: str
    slug: str
    category: str
    base_price: Decimal
    is_active: bool
    description: Optional[str] = None
    variants: List[CarVariant] = field(default_factory=list)
    colors: List[CarColor] = field(default_factory=list)
