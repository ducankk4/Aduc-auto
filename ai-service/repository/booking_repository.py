"""Test-drive booking data access backed by the backend leads API.

Maps the backend response envelope {"success": ..., "data": ...} into the
TestDriveBooking domain entity so no other layer sees raw API payloads.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from loguru import logger

from core.domain.booking import BookingStatus, TestDriveBooking
from core.exceptions import InfrastructureError
from core.interface.repository import IBookingRepository

_LEADS_PATH = "/api/v1/leads"


class BookingRepository(IBookingRepository):
    """Booking sink calling the backend leads API via httpx."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def create(
        self,
        vehicle_id: UUID,
        customer_name: str,
        phone: str,
        email: str,
        showroom_pref: Optional[str] = None,
    ) -> TestDriveBooking:
        """Register a test-drive booking and return the stored record."""
        body = {
            "vehicle_id": str(vehicle_id),
            "customer_name": customer_name,
            "phone": phone,
            "email": email,
            "showroom_pref": showroom_pref,
        }
        try:
            response = await self._client.post(_LEADS_PATH, json=body)
        except httpx.HTTPError as exc:
            raise InfrastructureError(f"Không gọi được backend API: {exc}") from exc

        if response.is_error:
            raise InfrastructureError(
                f"Backend API trả lỗi [status={response.status_code}, path={_LEADS_PATH}]"
            )

        data = response.json()["data"]
        logger.info(
            "Booking created [booking_id={}, vehicle_id={}]", data["id"], vehicle_id
        )
        return TestDriveBooking(
            id=UUID(data["id"]),
            vehicle_id=UUID(data["vehicle_id"]),
            customer_name=data["customer_name"],
            phone=data["phone"],
            email=data["email"],
            status=BookingStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            showroom_pref=data.get("showroom_pref"),
        )
