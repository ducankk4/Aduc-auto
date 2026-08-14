"""Test-drive booking domain entities.

The backend calls this concept a "lead"; here it is named after what it
means in this service: a customer's request to test drive a vehicle.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class BookingStatus(str, Enum):
    """Lifecycle status of a test-drive booking (mirrors backend lead status)."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    CONVERTED = "converted"


@dataclass(frozen=True)
class TestDriveBooking:
    """A test-drive request registered with the backend."""

    id: UUID
    vehicle_id: UUID
    customer_name: str
    phone: str
    email: str
    status: BookingStatus
    created_at: datetime
    showroom_pref: Optional[str] = None
