"""Unit tests for the `list_vehicles` tool's error handling — per
error-handling-logging.md #5, a tool must return error text instead of
letting a port exception propagate and break the graph.
"""

from __future__ import annotations

from ai_service.application.dto.vehicle import VehicleDetailDTO, VehicleSummaryDTO
from ai_service.application.tools.catalog_tools import build_catalog_tools
from ai_service.infrastructure.backend.exceptions import (
    BackendNotFoundError,
    BackendUnavailableError,
)


class _UnavailableBackendPort:
    async def list_vehicles(self, page: int = 1, limit: int = 20):
        raise BackendUnavailableError("backend down")

    async def get_vehicle_detail(self, slug: str):
        raise BackendUnavailableError("backend down")


class _EmptyBackendPort:
    async def list_vehicles(self, page: int = 1, limit: int = 20):
        return []

    async def get_vehicle_detail(self, slug: str):
        raise BackendNotFoundError("Vehicle not found")


class _WorkingBackendPort:
    async def list_vehicles(self, page: int = 1, limit: int = 20):
        return [
            VehicleSummaryDTO(
                id="00000000-0000-0000-0000-000000000001",
                name="VF8",
                slug="vf8",
                category="SUV",
                base_price=1_000_000_000,
                is_active=True,
            )
        ]

    async def get_vehicle_detail(self, slug: str):
        return VehicleDetailDTO(
            id="00000000-0000-0000-0000-000000000001",
            name="VF8",
            slug="vf8",
            category="SUV",
            description="A mid-size electric SUV.",
            base_price=1_000_000_000,
            is_active=True,
            variants=[],
            colors=[],
        )


async def test_list_vehicles_returns_error_text_when_backend_unavailable():
    tools = build_catalog_tools(_UnavailableBackendPort())
    list_vehicles = tools[0]

    result = await list_vehicles.ainvoke({"page": 1, "limit": 20})

    assert result.startswith("Error:")


async def test_list_vehicles_reports_empty_catalog_without_error():
    tools = build_catalog_tools(_EmptyBackendPort())
    list_vehicles = tools[0]

    result = await list_vehicles.ainvoke({"page": 1, "limit": 20})

    assert not result.startswith("Error:")


async def test_list_vehicles_formats_vehicles_from_backend():
    tools = build_catalog_tools(_WorkingBackendPort())
    list_vehicles = tools[0]

    result = await list_vehicles.ainvoke({"page": 1, "limit": 20})

    assert "VF8" in result
    assert "vf8" in result


async def test_get_vehicle_detail_returns_error_text_when_backend_unavailable():
    tools = build_catalog_tools(_UnavailableBackendPort())
    get_vehicle_detail = tools[1]

    result = await get_vehicle_detail.ainvoke({"slug": "vf8"})

    assert result.startswith("Error:")


async def test_get_vehicle_detail_returns_error_text_when_not_found():
    tools = build_catalog_tools(_EmptyBackendPort())
    get_vehicle_detail = tools[1]

    result = await get_vehicle_detail.ainvoke({"slug": "unknown-slug"})

    assert result.startswith("Error:")


async def test_get_vehicle_detail_formats_vehicle_from_backend():
    tools = build_catalog_tools(_WorkingBackendPort())
    get_vehicle_detail = tools[1]

    result = await get_vehicle_detail.ainvoke({"slug": "vf8"})

    assert "VF8" in result
    assert "mid-size electric SUV" in result
