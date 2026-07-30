"""Domain Constants and State Machine Transitions for the Orders Module."""

from enum import Enum


class OrderStatus(str, Enum):
    """Order Lifecycle Statuses."""

    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# Valid Order State Machine Transition Rules
VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.CONFIRMED, OrderStatus.REFUNDED],
    OrderStatus.CONFIRMED: [],  # Terminal state
    OrderStatus.CANCELLED: [],  # Terminal state
    OrderStatus.REFUNDED: [],   # Terminal state
}

DEFAULT_ORDERS_PAGE_SIZE = 20
