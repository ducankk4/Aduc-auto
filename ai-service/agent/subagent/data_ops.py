"""Data-ops subagent: vehicle data lookup and test-drive booking.

Declares the SubAgent spec consumed by create_deep_agent. The approval
gate (interrupt_on) is derived from each tool's requires_approval
metadata, so adding a sensitive tool never means touching this mapping.
"""

from typing import Any, Dict, List

from langchain_core.tools import BaseTool

from agent.prompt.prompts import DATA_OPS_SYSTEM_PROMPT
from agent.tools.booking import build_create_test_drive_booking_tool
from agent.tools.car import build_get_car_detail_tool, build_search_cars_tool
from agent.tools.constants import REQUIRES_APPROVAL
from services.booking_service import BookingService
from services.car_service import CarService

# Phase 2 decision: approve / edit / reject. "respond" is excluded because
# no data-ops tool is an "ask the human" style tool.
_ALLOWED_DECISIONS = ["approve", "edit", "reject"]


def _interrupt_on(tools: List[BaseTool]) -> Dict[str, Any]:
    """Map every tool flagged requires_approval to its approval config."""
    return {
        t.name: {"allowed_decisions": _ALLOWED_DECISIONS}
        for t in tools
        if (t.metadata or {}).get(REQUIRES_APPROVAL)
    }


def build_data_ops_subagent(
    car_service: CarService, booking_service: BookingService
) -> Dict[str, Any]:
    """Build the data-ops SubAgent spec for create_deep_agent.

    Args:
        car_service (CarService): Vehicle lookup use cases for view tools.
        booking_service (BookingService): Booking use case for the
            sensitive create_test_drive_booking tool.

    Returns:
        Dict[str, Any]: Declarative spec with tools and the derived
            interrupt_on map for sensitive tools.
    """
    tools: List[BaseTool] = [
        build_search_cars_tool(car_service),
        build_get_car_detail_tool(car_service),
        build_create_test_drive_booking_tool(booking_service),
    ]
    return {
        "name": "data-ops",
        "description": (
            "Tra cứu và thao tác dữ liệu xe: danh sách xe, giá, phiên bản, "
            "màu, đặt lịch lái thử."
        ),
        "system_prompt": DATA_OPS_SYSTEM_PROMPT,
        "tools": tools,
        "interrupt_on": _interrupt_on(tools),
    }
