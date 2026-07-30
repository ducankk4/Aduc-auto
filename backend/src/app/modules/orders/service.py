"""Business Logic & Service Interface for the Orders Module.

Implements Order State Machine, order creation, status transitions, and audit logging.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Tuple, List, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log as audit_log
from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError, ValidationError
from app.modules.catalog.service import CatalogService
from app.modules.orders.constants import OrderStatus, VALID_TRANSITIONS
from app.modules.orders.model import OrderModel, OrderStatusHistory
from app.modules.orders.repository import OrderRepository


class OrderService:
    """Order Domain Service orchestrating order creation, state transitions, and authorization."""

    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: Optional[UUID],
        variant_id: UUID,
        color_id: UUID,
        customer_name: str,
        phone: str,
        email: str,
        id_card: str,
    ) -> OrderModel:
        """Create a new car deposit order.

        Args:
            session (AsyncSession): Active database session.
            user_id (Optional[UUID]): Customer user UUID (or None for guest).
            variant_id (UUID): Selected vehicle variant UUID.
            color_id (UUID): Selected vehicle color UUID.
            customer_name (str): Customer full name.
            phone (str): Customer phone number.
            email (str): Customer email address.
            id_card (str): Citizen ID / Passport number.

        Returns:
            OrderModel: Created order ORM entity.

        Raises:
            NotFoundError: If variant or color does not exist.
            ValidationError: If color does not belong to the variant's vehicle.
        """
        # 1. Retrieve variant via catalog.service
        variant = await CatalogService.get_variant(session, variant_id)

        # 2. Retrieve color via catalog.service & validate matching vehicle
        color = await CatalogService.get_color(session, color_id)
        if color.vehicle_id != variant.vehicle_id:
            raise ValidationError("Màu sắc được chọn không thuộc dòng xe của phiên bản này")

        # Standard Deposit Amount (50,000,000 VND)
        deposit_amount = Decimal("50000000.00")

        # 3. Generate unique business order code
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        order_code = f"ORD-{date_str}-{uuid4().hex[:6].upper()}"

        # 4. Insert OrderModel with status="pending"
        order = OrderModel(
            order_code=order_code,
            user_id=user_id,
            variant_id=variant_id,
            color_id=color_id,
            deposit_amount=deposit_amount,
            status=OrderStatus.PENDING.value,
            customer_name=customer_name,
            phone=phone,
            email=email,
            id_card=id_card,
        )
        created_order = await OrderRepository.create_order(session, order)

        # 5. Insert initial OrderStatusHistory entry
        history_entry = OrderStatusHistory(
            order_id=created_order.id,
            from_status=None,
            to_status=OrderStatus.PENDING.value,
            changed_by=user_id,
            note="Khởi tạo đơn đặt cọc thành công",
        )
        await OrderRepository.create_status_history(session, history_entry)

        # 6. Audit log order creation
        await audit_log(
            session=session,
            user_id=user_id,
            action="order.created",
            resource="orders",
            resource_id=created_order.id,
            payload={"order_code": order_code, "deposit_amount": str(deposit_amount)},
        )

        return created_order

    @staticmethod
    async def get_by_code(
        session: AsyncSession,
        order_code: str,
        user_id: Optional[UUID] = None,
    ) -> OrderModel:
        """Retrieve order by order code with authorization check.

        Args:
            session (AsyncSession): Active database session.
            order_code (str): Unique business order code.
            user_id (Optional[UUID]): Customer user UUID to validate ownership (None skips check).

        Returns:
            OrderModel: Found order ORM entity.

        Raises:
            NotFoundError: If order code does not exist.
            ForbiddenError: If user_id is provided and does not match order owner.
        """
        order = await OrderRepository.find_by_code(session, order_code)
        if not order:
            raise NotFoundError(f"Không tìm thấy đơn hàng với mã: '{order_code}'")

        if user_id is not None and order.user_id != user_id:
            raise ForbiddenError("Bạn không có quyền truy cập thông tin đơn hàng này")

        return order

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        order_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> OrderModel:
        """Retrieve order by UUID primary key with authorization check.

        Args:
            session (AsyncSession): Active database session.
            order_id (UUID): Order primary key UUID.
            user_id (Optional[UUID]): Customer user UUID to validate ownership.

        Returns:
            OrderModel: Found order ORM entity.

        Raises:
            NotFoundError: If order does not exist.
            ForbiddenError: If user_id is provided and does not match order owner.
        """
        order = await OrderRepository.find_by_id(session, order_id)
        if not order:
            raise NotFoundError(f"Không tìm thấy đơn hàng với ID: '{order_id}'")

        if user_id is not None and order.user_id != user_id:
            raise ForbiddenError("Bạn không có quyền truy cập thông tin đơn hàng này")

        return order

    @staticmethod
    async def update_status(
        session: AsyncSession,
        order_id: UUID,
        new_status: str,
        changed_by: Optional[UUID] = None,
        note: Optional[str] = None,
    ) -> OrderModel:
        """Enforce state machine transition rules and update order status.

        State Machine Transitions:
        - pending -> paid, cancelled
        - paid -> confirmed, refunded
        - confirmed -> (terminal)
        - cancelled -> (terminal)
        - refunded -> (terminal)

        Args:
            session (AsyncSession): Active database session.
            order_id (UUID): Order primary key UUID.
            new_status (str): Target state transition status.
            changed_by (Optional[UUID]): User UUID performing the status change.
            note (Optional[str]): Operational note/reason.

        Returns:
            OrderModel: Updated order ORM entity.

        Raises:
            NotFoundError: If order is not found.
            ConflictError: If state transition is invalid according to state machine rules.
        """
        order = await OrderRepository.find_by_id(session, order_id)
        if not order:
            raise NotFoundError(f"Không tìm thấy đơn hàng với ID: '{order_id}'")

        current_status = order.status
        allowed_transitions = VALID_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise ConflictError(
                f"Chuyển trạng thái đơn hàng không hợp lệ: KHÔNG THỂ chuyển từ '{current_status}' sang '{new_status}'. "
                f"Các trạng thái cho phép: {allowed_transitions or 'Không có (Trạng thái kết thúc)'}"
            )

        # 2. Update order status
        order.status = new_status
        await session.flush()

        # 3. Record status history entry
        history_entry = OrderStatusHistory(
            order_id=order.id,
            from_status=current_status,
            to_status=new_status,
            changed_by=changed_by,
            note=note,
        )
        await OrderRepository.create_status_history(session, history_entry)

        # 4. Audit log status update
        await audit_log(
            session=session,
            user_id=changed_by,
            action="order.status_updated",
            resource="orders",
            resource_id=order.id,
            payload={
                "from_status": current_status,
                "to_status": new_status,
                "note": note,
            },
        )

        return order

    @staticmethod
    async def list_user_orders(
        session: AsyncSession,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[OrderModel], int]:
        """Fetch paginated orders created by a specific user."""
        return await OrderRepository.find_user_orders(session, user_id=user_id, page=page, limit=limit)

    @staticmethod
    async def list_all_orders(
        session: AsyncSession,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[OrderModel], int]:
        """Fetch paginated orders for admin portal."""
        return await OrderRepository.find_all_orders(session, status_filter=status_filter, page=page, limit=limit)
