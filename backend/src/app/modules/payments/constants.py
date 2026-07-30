"""Domain Constants for the Payments Module."""

from enum import Enum


class PaymentStatus(str, Enum):
    """Payment Lifecycle Statuses."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentMethod(str, Enum):
    """Payment Gateway Methods."""

    VNPAY = "vnpay"
    BANK_TRANSFER = "bank_transfer"
