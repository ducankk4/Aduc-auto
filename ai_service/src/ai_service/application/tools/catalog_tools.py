"""Read-only catalog tools exposed to the supervisor agent."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from loguru import logger

from ai_service.application.dto.vehicle import VehicleDetailDTO, VehicleSummaryDTO
from ai_service.application.ports.backend_port import BackendPort
from ai_service.infrastructure.backend.exceptions import BackendError, BackendUnavailableError


def build_catalog_tools(backend_port: BackendPort) -> list[BaseTool]:
    """Build the catalog toolset bound to a concrete BackendPort implementation."""

    @tool
    async def list_vehicles(page: int = 1, limit: int = 20) -> str:
        """List vehicles currently in the catalog, paginated.

        Use when the user wants an overview of available vehicles (e.g. "what
        cars do you have?", "show me some options"). Do NOT use this to get
        full detail of one already-known vehicle — use `get_vehicle_detail`
        for that instead.

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

    @tool
    async def get_vehicle_detail(slug: str) -> str:
        """Get full detail of a single vehicle by slug, including variants and colors.

        Use when the user asks about the price, configuration, or specs of ONE
        specific vehicle whose slug is already known (e.g. from a prior
        `list_vehicles` call). Do not use this to search or list multiple
        vehicles — use `list_vehicles` for that. To compare several vehicles,
        call this tool once per vehicle slug.

        Args:
            slug: URL slug identifying the vehicle, e.g. "vf8-2026".

        Returns:
            Formatted text describing the vehicle (name, category, description,
            base price, variants, colors) ready for the model to read. Returns
            an error message if the vehicle is not found or the catalog is
            unreachable — this is a tool result exchanged between the tool
            and the agent, not the reply shown to the end user.
        """
        try:
            vehicle = await backend_port.get_vehicle_detail(slug)
        except BackendUnavailableError as err:
            logger.bind(slug=slug, operation="get_vehicle_detail").warning(
                "Backend unavailable: {}", err
            )
            return "Error: the vehicle catalog is temporarily unavailable, please try again later."
        except BackendError as err:
            return f"Error: {err.message}"

        return _format_vehicle_detail(vehicle)

    return [list_vehicles, get_vehicle_detail]


def _format_vehicle_list(vehicles: list[VehicleSummaryDTO]) -> str:
    lines: list[str] = []
    for vehicle in vehicles:
        status = "" if vehicle.is_active else " [discontinued]"
        lines.append(
            f"- {vehicle.name} ({vehicle.category}), slug={vehicle.slug}, "
            f"list price: {vehicle.base_price:,.0f} VND{status}"
        )
    return "Vehicle list:\n" + "\n".join(lines)


def _format_vehicle_detail(vehicle: VehicleDetailDTO) -> str:
    status = "" if vehicle.is_active else " [discontinued]"
    lines = [
        f"{vehicle.name} ({vehicle.category}), slug={vehicle.slug}{status}",
        f"Base price: {vehicle.base_price:,.0f} VND",
    ]
    if vehicle.description:
        lines.append(f"Description: {vehicle.description}")

    if vehicle.variants:
        lines.append("Variants:")
        lines.extend(
            f"  - {v.name} (sku={v.sku}): {v.price:,.0f} VND" for v in vehicle.variants
        )
    else:
        lines.append("Variants: none listed")

    if vehicle.colors:
        lines.append("Colors:")
        lines.extend(
            f"  - {c.name} ({c.color_code}): +{c.price_extra:,.0f} VND"
            for c in vehicle.colors
        )
    else:
        lines.append("Colors: none listed")

    return "\n".join(lines)
