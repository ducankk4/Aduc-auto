"""Unit Tests for Order Service State Machine Transitions."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest

from app.core.exceptions import ConflictError
from app.modules.orders.constants import OrderStatus
from app.modules.orders.model import OrderModel
from app.modules.orders.service import OrderService


@pytest.mark.asyncio
async def test_valid_state_transitions():
    """Test ALL valid order state machine transitions."""
    valid_cases = [
        (OrderStatus.PENDING.value, OrderStatus.PAID.value),
        (OrderStatus.PENDING.value, OrderStatus.CANCELLED.value),
        (OrderStatus.PAID.value, OrderStatus.CONFIRMED.value),
        (OrderStatus.PAID.value, OrderStatus.REFUNDED.value),
    ]

    for from_status, to_status in valid_cases:
        session_mock = AsyncMock()
        fake_order_id = uuid4()
        fake_order = OrderModel(id=fake_order_id, status=from_status, history=[])

        with patch("app.modules.orders.repository.OrderRepository.find_by_id", return_value=fake_order), \
             patch("app.modules.orders.repository.OrderRepository.create_status_history", new_callable=AsyncMock), \
             patch("app.modules.orders.service.audit_log", new_callable=AsyncMock):

            updated_order = await OrderService.update_status(
                session=session_mock,
                order_id=fake_order_id,
                new_status=to_status,
                note=f"Test transition {from_status} -> {to_status}",
            )
            assert updated_order.status == to_status


@pytest.mark.asyncio
async def test_invalid_state_transitions_raise_conflict_error():
    """Test ALL invalid order state machine transitions raise ConflictError (HTTP 409)."""
    invalid_cases = [
        (OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value),
        (OrderStatus.PENDING.value, OrderStatus.REFUNDED.value),
        (OrderStatus.PAID.value, OrderStatus.PENDING.value),
        (OrderStatus.PAID.value, OrderStatus.CANCELLED.value),
        (OrderStatus.CONFIRMED.value, OrderStatus.PAID.value),
        (OrderStatus.CONFIRMED.value, OrderStatus.CANCELLED.value),
        (OrderStatus.CANCELLED.value, OrderStatus.PAID.value),
        (OrderStatus.REFUNDED.value, OrderStatus.PAID.value),
    ]

    for from_status, to_status in invalid_cases:
        session_mock = AsyncMock()
        fake_order_id = uuid4()
        fake_order = OrderModel(id=fake_order_id, status=from_status, history=[])

        with patch("app.modules.orders.repository.OrderRepository.find_by_id", return_value=fake_order):
            with pytest.raises(ConflictError) as exc_info:
                await OrderService.update_status(
                    session=session_mock,
                    order_id=fake_order_id,
                    new_status=to_status,
                )

            assert "KHÔNG THỂ chuyển từ" in str(exc_info.value.detail)
            assert from_status in str(exc_info.value.detail)
