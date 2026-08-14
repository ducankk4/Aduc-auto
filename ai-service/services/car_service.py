"""Use cases for vehicle catalog lookup."""

from typing import List, Tuple

from core.domain.car import Car
from core.exceptions import NotFoundError
from core.interface.repository import ICarRepository


class CarService:
    """Use cases for vehicle catalog lookup."""

    def __init__(self, car_repository: ICarRepository) -> None:
        self._car_repository = car_repository

    async def list_cars(self, page: int = 1, limit: int = 20) -> Tuple[List[Car], int]:
        """Return one page of active vehicles and the total vehicle count.

        Args:
            page (int): 1-based page number.
            limit (int): Page size.

        Returns:
            Tuple[List[Car], int]: Vehicles on this page and the total count.
        """
        return await self._car_repository.find_many(page=page, limit=limit)

    async def get_car(self, slug: str) -> Car:
        """Return the vehicle with the given slug.

        Args:
            slug (str): URL-friendly vehicle identifier.

        Returns:
            Car: The matching vehicle entity.

        Raises:
            NotFoundError: If no vehicle matches the given slug.
        """
        car = await self._car_repository.find_by_slug(slug)
        if car is None:
            raise NotFoundError(f"Không tìm thấy xe: {slug}")
        return car
