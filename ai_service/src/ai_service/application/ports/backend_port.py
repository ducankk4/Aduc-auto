"""Port describing what ai-service needs from the `backend` API.

Implemented by `infrastructure.backend.client.BackendHttpClient`. Tools and
use cases depend on this protocol only — never on httpx directly (see
code-style.md #6).
"""

from __future__ import annotations

from typing import Protocol

from ai_service.application.dto.vehicle import VehicleSummaryDTO


class BackendPort(Protocol):
    async def list_vehicles(self, page: int = 1, limit: int = 20) -> list[VehicleSummaryDTO]:
        """Return one page of vehicles from the catalog.

        Args:
            page: 1-based page number.
            limit: Number of vehicles per page.

        Raises:
            BackendUnavailableError: backend is unreachable or timed out.
            BackendError: backend returned an unexpected error response.
        """
        ...
