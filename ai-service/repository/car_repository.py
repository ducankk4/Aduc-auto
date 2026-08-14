"""Vehicle catalog data access backed by the backend HTTP API.

Maps the backend response envelope {"success": ..., "data": ...} into
pure domain entities so no other layer ever sees raw API payloads.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from loguru import logger

from core.domain.car import Car, CarColor, CarVariant
from core.exceptions import InfrastructureError
from core.interface.repository import ICarRepository

_VEHICLES_PATH = "/api/v1/catalog/vehicles"


class CarRepository(ICarRepository):
    """Vehicle data source calling the backend catalog API via httpx."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_many(self, page: int = 1, limit: int = 20) -> Tuple[List[Car], int]:
        """Return a page of active vehicles and the total vehicle count.

        Args:
            page (int): 1-based page number.
            limit (int): Maximum records per page.

        Returns:
            Tuple[List[Car], int]: Vehicles on this page and total count.

        Raises:
            InfrastructureError: If the backend API call fails.
        """
        payload = await self._get(_VEHICLES_PATH, params={"page": page, "limit": limit})
        cars = [_to_domain(item) for item in payload["data"]]
        total = payload.get("meta", {}).get("total", len(cars))
        logger.debug("Fetched vehicles [page={}, count={}, total={}]", page, len(cars), total)
        return cars, total

    async def find_by_slug(self, slug: str) -> Optional[Car]:
        """Return the vehicle matching the given slug, or None if absent.

        Args:
            slug (str): Unique vehicle URL slug.

        Returns:
            Optional[Car]: The matching vehicle, or None when the backend
                answers 404.

        Raises:
            InfrastructureError: If the backend API call fails for any
                reason other than a 404.
        """
        try:
            payload = await self._get(f"{_VEHICLES_PATH}/{slug}")
        except _NotFound:
            return None
        return _to_domain(payload["data"])

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a GET request and unwrap backend errors into our hierarchy."""
        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise InfrastructureError(f"Không gọi được backend API: {exc}") from exc

        if response.status_code == 404:
            raise _NotFound()
        if response.is_error:
            raise InfrastructureError(
                f"Backend API trả lỗi [status={response.status_code}, path={path}]"
            )
        return response.json()


class _NotFound(Exception):
    """Internal marker: backend answered 404 for a lookup."""


def _to_domain(data: Dict[str, Any]) -> Car:
    """Map one vehicle payload from the backend API into a Car entity."""
    return Car(
        id=UUID(data["id"]),
        name=data["name"],
        slug=data["slug"],
        category=data["category"],
        base_price=Decimal(str(data["base_price"])),
        is_active=data["is_active"],
        description=data.get("description"),
        variants=[
            CarVariant(
                id=UUID(v["id"]),
                name=v["name"],
                sku=v["sku"],
                price=Decimal(str(v["price"])),
            )
            for v in data.get("variants", [])
        ],
        colors=[
            CarColor(
                id=UUID(c["id"]),
                name=c["name"],
                color_code=c["color_code"],
                price_extra=Decimal(str(c["price_extra"])),
            )
            for c in data.get("colors", [])
        ],
    )
