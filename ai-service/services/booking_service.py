"""Use cases for test-drive booking."""

from typing import Optional

from loguru import logger

from core.domain.booking import TestDriveBooking
from core.exceptions import NotFoundError
from core.interface.repository import IBookingRepository, ICarRepository


class BookingService:
    """Use cases for registering test-drive bookings."""

    def __init__(
        self,
        booking_repository: IBookingRepository,
        car_repository: ICarRepository,
    ) -> None:
        self._booking_repository = booking_repository
        self._car_repository = car_repository

    async def create_test_drive_booking(
        self,
        car_slug: str,
        customer_name: str,
        phone: str,
        email: str,
        showroom_pref: Optional[str] = None,
    ) -> TestDriveBooking:
        """Register a test drive for the vehicle identified by its slug.

        Args:
            car_slug (str): URL-friendly identifier of the vehicle to test drive.
            customer_name (str): Customer's full name.
            phone (str): Customer's contact phone number.
            email (str): Customer's contact email.
            showroom_pref (Optional[str]): Preferred showroom, if any.

        Returns:
            TestDriveBooking: The booking as stored by the backend.

        Raises:
            NotFoundError: If no vehicle matches the given slug.
            InfrastructureError: If the backend call fails.
        """
        car = await self._car_repository.find_by_slug(car_slug)
        if car is None:
            raise NotFoundError(f"Không tìm thấy xe: {car_slug}")

        booking = await self._booking_repository.create(
            vehicle_id=car.id,
            customer_name=customer_name,
            phone=phone,
            email=email,
            showroom_pref=showroom_pref,
        )
        logger.info(
            "Test drive booked [booking_id={}, car_slug={}]", booking.id, car_slug
        )
        return booking
