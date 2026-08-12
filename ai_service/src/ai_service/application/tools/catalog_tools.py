"""Read-only catalog tools exposed to the supervisor agent."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from loguru import logger

from ai_service.application.dto.vehicle import VehicleSummaryDTO
from ai_service.application.ports.backend_port import BackendPort
from ai_service.infrastructure.backend.exceptions import BackendError, BackendUnavailableError


def build_catalog_tools(backend_port: BackendPort) -> list[BaseTool]:
    """Build the catalog toolset bound to a concrete BackendPort implementation."""

    @tool
    async def list_vehicles(page: int = 1, limit: int = 20) -> str:
        """List vehicles currently in the catalog, paginated.

        Use when the user wants an overview of available vehicles (e.g. "what
        cars do you have?", "show me some options"). Do NOT use this to get
        full detail of one already-known vehicle — a dedicated detail tool
        will be added separately once available.

        Args:
            page: 1-based page number.
            limit: Number of vehicles per page (1-100).

        Returns:
            Formatted text listing vehicle name, category, and base price,
            ready for the model to read and present to the user. Returns an
            English error message if the catalog cannot be reached — this is
            a tool result exchanged with the agent, not the reply shown to
            the end user, so it follows code language (English).
        """
        try:
            vehicles = await backend_port.list_vehicles(page=page, limit=limit)
        except BackendUnavailableError as err:
            logger.bind(operation="list_vehicles").warning("Backend unavailable: {}", err)
            return "Error: the vehicle catalog is temporarily unavailable, please try again later."
        except BackendError as err:
            return f"Error: {err.message}"

        if not vehicles:
            return "No vehicles found in the catalog on this page."

        return _format_vehicle_list(vehicles)

    return [list_vehicles]


def _format_vehicle_list(vehicles: list[VehicleSummaryDTO]) -> str:
    lines: list[str] = []
    for vehicle in vehicles:
        status = "" if vehicle.is_active else " [discontinued]"
        lines.append(
            f"- {vehicle.name} ({vehicle.category}), slug={vehicle.slug}, "
            f"list price: {vehicle.base_price:,.0f} VND{status}"
        )
    return "Vehicle list:\n" + "\n".join(lines)
