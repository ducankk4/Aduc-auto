"""Vehicle catalog tools for the data-ops subagent.

Tools contain no business logic: they parse arguments, call the injected
service, and format the result for the LLM. Logic lives in services/.
"""

from langchain_core.tools import BaseTool, tool

from core.domain.car import Car
from core.exceptions import NotFoundError
from services.car_service import CarService


def _format_car_line(car: Car) -> str:
    """One list row: enough to pick a car and grab its slug."""
    return f"- {car.name} (slug: {car.slug}) — {car.category}, giá từ {car.base_price:,.0f} VND"


def _format_car_detail(car: Car) -> str:
    """Full detail block: price, variants, colors, description."""
    lines = [
        f"Xe: {car.name} (slug: {car.slug})",
        f"Phân khúc: {car.category}",
        f"Giá cơ bản: {car.base_price:,.0f} VND",
    ]
    if car.description:
        lines.append(f"Mô tả: {car.description}")
    if car.variants:
        lines.append("Phiên bản:")
        lines.extend(f"  - {v.name} (SKU {v.sku}): {v.price:,.0f} VND" for v in car.variants)
    if car.colors:
        lines.append("Màu sắc:")
        lines.extend(
            f"  - {c.name} ({c.color_code}): +{c.price_extra:,.0f} VND" for c in car.colors
        )
    return "\n".join(lines)


def build_search_cars_tool(car_service: CarService) -> BaseTool:
    """Build the search_cars view tool bound to the given CarService."""

    @tool
    async def search_cars(page: int = 1) -> str:
        """Liệt kê xe đang bán của Aduc Auto: tên, slug, phân khúc, giá cơ bản.

        Gọi tool này khi khách hỏi đang có những xe nào, hoặc để tìm slug
        của một xe trước khi xem chi tiết / đặt lịch lái thử.

        Args:
            page: Trang danh sách, bắt đầu từ 1.
        """
        cars, total = await car_service.list_cars(page=page)
        if not cars:
            return "Không có xe nào trong danh mục."
        header = f"Tổng cộng {total} xe. Trang {page}:"
        return "\n".join([header, *(_format_car_line(car) for car in cars)])

    return search_cars


def build_get_car_detail_tool(car_service: CarService) -> BaseTool:
    """Build the get_car_detail view tool bound to the given CarService."""

    @tool
    async def get_car_detail(car_slug: str) -> str:
        """Xem chi tiết một xe: giá, các phiên bản, màu sắc kèm phụ phí, mô tả.

        Args:
            car_slug: Slug của xe, lấy từ kết quả search_cars.
        """
        try:
            car = await car_service.get_car(car_slug)
        except NotFoundError:
            return (
                f"Không tìm thấy xe với slug '{car_slug}'. "
                "Dùng search_cars để xem danh sách slug đúng."
            )
        return _format_car_detail(car)

    return get_car_detail
