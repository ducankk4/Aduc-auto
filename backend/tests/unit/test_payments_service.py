"""Unit Tests for Payments Service & Webhook Idempotency Flow."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import pytest

from app.modules.orders.model import OrderModel
from app.modules.payments.model import PaymentModel
from app.modules.payments.service import PaymentService


@pytest.mark.asyncio
async def test_webhook_idempotency_flow():
    """Verify webhook called 2 times with identical transaction_code only updates order status ONCE."""
    session_mock = AsyncMock()
    fake_order_id = uuid4()
    fake_txn_code = "14598210"

    fake_order = OrderModel(
        id=fake_order_id,
        order_code="ORD-20260730-TEST01",
        deposit_amount=Decimal("50000000.00"),
        status="pending",
    )
    fake_payment = PaymentModel(
        id=uuid4(),
        order_id=fake_order_id,
        amount=Decimal("50000000.00"),
        status="pending",
    )
    successful_payment = PaymentModel(
        id=uuid4(),
        order_id=fake_order_id,
        amount=Decimal("50000000.00"),
        status="success",
        transaction_code=fake_txn_code,
    )

    raw_payload = {
        "vnp_Amount": "5000000000",
        "vnp_ResponseCode": "00",
        "vnp_TransactionNo": fake_txn_code,
        "vnp_TxnRef": "ORD-20260730-TEST01",
        "vnp_SecureHash": "valid_hash",
    }

    with patch("app.modules.payments.gateways.vnpay.verify_signature", return_value=True), \
         patch("app.modules.orders.service.OrderService.get_by_code", return_value=fake_order), \
         patch("app.modules.orders.service.OrderService.update_status", new_callable=AsyncMock) as mock_order_update_status, \
         patch("app.modules.payments.repository.PaymentRepository.create_payment", return_value=fake_payment), \
         patch("app.modules.payments.service.send_order_confirmation", new_callable=AsyncMock):

        # First webhook call: Not in database yet
        with patch("app.modules.payments.repository.PaymentRepository.find_successful_transaction", return_value=None), \
             patch("app.modules.payments.repository.PaymentRepository.find_by_order_id", return_value=fake_payment):

            res1 = await PaymentService.handle_webhook(session=session_mock, raw_payload=raw_payload)
            assert res1 == {"RspCode": "00", "Message": "Confirm Success"}
            assert mock_order_update_status.call_count == 1

        # Second webhook call (duplicate retry): Existing transaction returned
        with patch("app.modules.payments.repository.PaymentRepository.find_successful_transaction", return_value=successful_payment):
            res2 = await PaymentService.handle_webhook(session=session_mock, raw_payload=raw_payload)
            assert res2 == {"RspCode": "00", "Message": "Confirm Success"}
            # Order update status MUST NOT be called again
            assert mock_order_update_status.call_count == 1
