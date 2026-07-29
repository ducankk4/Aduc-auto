"""Domain Constants for the Users Module."""

from enum import Enum


class DefaultRole(str, Enum):
    """System Default Roles."""

    ADMIN = "admin"
    SALE = "sale"
    CUSTOMER = "customer"


# Login throttling constraints
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOGIN_THROTTLE_WINDOW_SECONDS = 60
