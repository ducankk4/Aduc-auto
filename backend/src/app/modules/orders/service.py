"""Orders Module — Business Logic & State Machine Service Layer.

State Machine transitions:
pending   -> paid, cancelled
paid      -> confirmed, refunded
confirmed -> []
cancelled -> []
refunded  -> []

Depends on catalog module via catalog.service and users module via users.service.
"""

VALID_TRANSITIONS = {
    "pending": ["paid", "cancelled"],
    "paid": ["confirmed", "refunded"],
    "confirmed": [],
    "cancelled": [],
    "refunded": [],
}

# Public service interfaces will be implemented in Phase 2
