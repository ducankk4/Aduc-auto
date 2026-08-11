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
            ready for the model to read and present to the user. Returns a
            Vietnamese-language error message if the catalog cannot be
            reached — that message is user-facing conversation content, not
            code, so it follows the product's chat language.
        """
        try:
            vehicles = await backend_port.list_vehicles(page=page, limit=limit)
        except BackendUnavailableError as err:
            logger.bind(operation="list_vehicles").warning("Backend unavailable: {}", err)
            return "Error: hệ thống danh mục xe tạm thời không truy cập được, vui lòng thử lại sau."
        except BackendError as err:
            return f"Error: {err.message}"

        if not vehicles:
            return "Không có mẫu xe nào trong danh mục ở trang này."

        return _format_vehicle_list(vehicles)

    return [list_vehicles]


def _format_vehicle_list(vehicles: list[VehicleSummaryDTO]) -> str:
    lines: list[str] = []
    for vehicle in vehicles:
        status = "" if vehicle.is_active else " [ngừng kinh doanh]"
        lines.append(
            f"- {vehicle.name} ({vehicle.category}), slug={vehicle.slug}, "
            f"giá niêm yết: {vehicle.base_price:,.0f} VND{status}"
        )
    return "Danh sách xe:\n" + "\n".join(lines)
