"""Internal DTOs mirroring the subset of backend response shapes ai-service
needs. Deliberately separate from backend's own Pydantic schemas — ai-service
does not import backend code (code-style.md #4).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VehicleSummarySchema(BaseModel):
    """Subset of backend's VehicleResponseSchema needed to summarize a
    vehicle in chat. Extra fields (variants, colors, description, ...) are
    ignored — this is not the schema for full vehicle detail.
    """

    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    slug: str
    category: str
    base_price: Decimal
    is_active: bool
