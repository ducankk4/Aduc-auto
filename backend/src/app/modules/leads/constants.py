"""Domain Constants and Enums for the Leads Module."""

from enum import Enum


class LeadStatus(str, Enum):
    """Lead Status Lifecycle Transitions."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    CONVERTED = "converted"


DEFAULT_LEADS_PAGE_SIZE = 20
MAX_LEADS_PER_MINUTE_PER_IP = 10
