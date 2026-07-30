"""Business Logic & Service Interface for the Payments Module.

Implements VNPay Payment Initialization and Atomic Idempotent Webhook Processing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.orders.service import OrderService
from app.modules.payments.gateways import vnpay
from app.modules.payments.model import PaymentModel
from app.modules.payments.repository import PaymentRepository
from app.workers.email import send_order_confirmation

logger = logging.getLogger(__name__)


class PaymentService:
    """Payment Service orchestrating VNPay payments and atomic webhook processing."""

    @staticmethod
    async def initiate_payment(
        session: AsyncSession,
        order_id: UUID,
        user_id: Optional[UUID] = None,
        return_url: Optional[str] = None,
    ) -> PaymentModel:
        """Initiate payment process for a deposit order and generate signed VNPay redirect URL.

        Args:
            session (AsyncSession): Active database session.
            order_id (UUID): Order primary key UUID.
            user_id (Optional[UUID]): User UUID performing request (for ownership check).
            return_url (Optional[str]): Return URL after payment completion.

        Returns:
            PaymentModel: Updated payment record containing payment_url.

        Raises:
            NotFoundError: If order does not exist.
            ConflictError: If order is not in 'pending' status.
        """
        # 1. Retrieve order via orders.service (inter-module boundary)
        order = await OrderService.get_by_id(session, order_id, user_id=user_id)

        if order.status != "pending":
            raise ConflictError(
                f"Đơn hàng '{order.order_code}' đang ở trạng thái '{order.status}', không thể tạo thanh toán."
            )

        # 2. Retrieve or create payment record
        payment = await PaymentRepository.find_by_order_id(session, order.id)
        if not payment:
            payment = PaymentModel(
                order_id=order.id,
                amount=order.deposit_amount,
                payment_method="vnpay",
                status="pending",
            )
            payment = await PaymentRepository.create_payment(session, payment)

        # 3. Generate signed VNPay URL
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        target_return_url = return_url or settings.VNPAY_RETURN_URL

        payment_url = vnpay.build_payment_url(
            vnpay_url=settings.VNPAY_URL,
            secret_key=settings.VNPAY_HASH_SECRET,
            tmn_code=settings.VNPAY_TMN_CODE,
            order_code=order.order_code,
            amount=float(order.deposit_amount),
            order_info=f"Dat coc xe don hang {order.order_code}",
            return_url=target_return_url,
            create_date_str=now_str,
        )

        payment.payment_url = payment_url
        await session.flush()
        return payment

    @staticmethod
    async def handle_webhook(
        session: AsyncSession,
        raw_payload: Dict[str, Any],
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, str]:
        """Process incoming VNPay IPN Webhook using strict 5-step Idempotent Flow.

        Step 1: Verify HMAC-SHA512 checksum signature.
        Step 2: Check Idempotency (if transaction already successfully processed, return immediately).
        Step 3: Update Payment record (in same session with Step 4 to ensure single atomic DB transaction).
        Step 4: Update Order status via orders.service (OrderService.update_status).
        Step 5: Trigger background task to send order confirmation email.

        Args:
            session (AsyncSession): Active database session shared with request transaction.
            raw_payload (Dict[str, Any]): Dictionary of incoming query parameters or body payload.
            background_tasks (Optional[BackgroundTasks]): FastAPI background tasks framework.

        Returns:
            Dict[str, str]: VNPay standard response dictionary `{"RspCode": "00", "Message": "Confirm Success"}`.
        """
        # Step 1: Verify signature
        if not vnpay.verify_signature(raw_payload, settings.VNPAY_HASH_SECRET):
            logger.warning("⚠️ VNPay Webhook: Chữ ký không hợp lệ (Invalid Checksum)")
            return {"RspCode": "97", "Message": "Invalid Checksum"}

        txn_code = str(raw_payload.get("vnp_TransactionNo") or raw_payload.get("vnp_TxnRef", ""))
        order_code = str(raw_payload.get("vnp_TxnRef", ""))
        vnp_response_code = raw_payload.get("vnp_ResponseCode")

        if vnp_response_code != "00":
            logger.warning(f"⚠️ VNPay Webhook: Giao dịch không thành công [ResponseCode={vnp_response_code}]")
            return {"RspCode": "00", "Message": "Confirm Success"}

        # Step 2: Idempotency check — check if transaction_code already processed as success
        existing_success = await PaymentRepository.find_successful_transaction(session, txn_code)
        if existing_success:
            logger.info(f"ℹ️ VNPay Webhook: Transaction [{txn_code}] đã được xử lý thành công trước đó (Idempotent return)")
            return {"RspCode": "00", "Message": "Confirm Success"}

        # Step 3: Update Payment (atomic with Step 4)
        order = await OrderService.get_by_code(session, order_code)
        payment = await PaymentRepository.find_by_order_id(session, order.id)
        if not payment:
            payment = PaymentModel(
                order_id=order.id,
                amount=order.deposit_amount,
                payment_method="vnpay",
            )
            payment = await PaymentRepository.create_payment(session, payment)

        payment.status = "success"
        payment.transaction_code = txn_code
        payment.paid_at = datetime.now(timezone.utc)
        await session.flush()

        # Step 4: Update Order status via orders/service (inter-module public call)
        await OrderService.update_status(
            session=session,
            order_id=order.id,
            new_status="paid",
            note=f"VNPay webhook confirmed (TxnNo: {txn_code})",
        )

        # Step 5: Trigger background task to send confirmation email
        if background_tasks:
            background_tasks.add_task(send_order_confirmation, order.id)
        else:
            asyncio.create_task(send_order_confirmation(order.id))

        return {"RspCode": "00", "Message": "Confirm Success"}
