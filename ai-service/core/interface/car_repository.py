"""Contract for vehicle catalog data access."""

from typing import List, Optional, Protocol, Tuple

from core.domain.car import Car


class CarRepositoryProtocol(Protocol):
    """Contract any vehicle data source must satisfy."""

    async def find_many(self, page: int = 1, limit: int = 20) -> Tuple[List[Car], int]:
        """Return a page of active vehicles and the total vehicle count."""
        ...

    async def find_by_slug(self, slug: str) -> Optional[Car]:
        """Return the vehicle matching the given slug, or None if absent."""
        ...
