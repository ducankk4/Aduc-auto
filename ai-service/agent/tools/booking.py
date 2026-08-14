"""Booking tools for the data-ops subagent.

Tools contain no business logic: they parse arguments, call the injected
service, and format the result for the LLM. Logic lives in services/.
"""

from typing import Optional

from langchain_core.tools import BaseTool, tool

from agent.tools.constants import REQUIRES_APPROVAL
from core.exceptions import NotFoundError
from services.booking_service import BookingService


def build_create_test_drive_booking_tool(booking_service: BookingService) -> BaseTool:
    """Build the sensitive create_test_drive_booking tool.

    Returns:
        BaseTool: Tool flagged with requires_approval metadata, so the
            data-ops subagent puts it behind the HITL approval gate.
    """

    @tool
    async def create_test_drive_booking(
        car_slug: str,
        customer_name: str,
        phone: str,
        email: str,
        showroom_pref: Optional[str] = None,
    ) -> str:
        """Đăng ký lịch lái thử xe cho khách hàng.

        CHỈ gọi tool này khi đã có đủ: slug của xe (tra bằng search_cars
        nếu chưa chắc), họ tên khách, số điện thoại và email. Thiếu thông
        tin nào thì KHÔNG gọi tool — trả lời nêu rõ cần hỏi khách thông
        tin gì.

        Args:
            car_slug: Slug của xe khách muốn lái thử, lấy từ search_cars.
            customer_name: Họ tên đầy đủ của khách hàng.
            phone: Số điện thoại liên hệ của khách.
            email: Email liên hệ của khách.
            showroom_pref: Showroom khách muốn đến (tùy chọn).
        """
        try:
            booking = await booking_service.create_test_drive_booking(
                car_slug=car_slug,
                customer_name=customer_name,
                phone=phone,
                email=email,
                showroom_pref=showroom_pref,
            )
        except NotFoundError:
            return (
                f"Không tìm thấy xe với slug '{car_slug}'. "
                "Dùng search_cars để tra slug đúng rồi thử lại."
            )
        return (
            f"Đã ghi nhận đăng ký lái thử (mã {booking.id}) cho khách "
            f"{booking.customer_name}. Showroom sẽ liên hệ qua số điện thoại "
            "đã cung cấp để xác nhận lịch."
        )

    create_test_drive_booking.metadata = {REQUIRES_APPROVAL: True}
    return create_test_drive_booking
