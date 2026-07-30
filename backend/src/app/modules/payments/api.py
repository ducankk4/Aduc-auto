"""FastAPI Presentation Layer (Routers) for the Payments Module."""

from typing import Dict, Any, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import success
from app.modules.payments.schema import PaymentInitResponseSchema
from app.modules.payments.service import PaymentService

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]

payments_router = APIRouter(prefix="/payments", tags=["Payments"])

@payments_router.post("/{order_id}/init")
async def initiate_payment(
    order_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
):
    """Customer endpoint to initiate VNPay payment for a deposit order."""
    user_id = UUID(current_user["sub"])
    payment = await PaymentService.initiate_payment(
        session=session,
        order_id=order_id,
        user_id=user_id,
    )
    data = {
        "payment_id": str(payment.id),
        "order_id": str(payment.order_id),
        "amount": str(payment.amount),
        "payment_url": payment.payment_url,
    }
    return success(data=data)


@payments_router.api_route("/webhook", methods=["GET", "POST"])
async def vnpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DBSession,
):
    """Public VNPay IPN Webhook endpoint.

    ALWAYS returns HTTP 200 status code regardless of validation outcome per VNPay spec.
    """
    if request.method == "POST":
        form_data = await request.form()
        params = dict(form_data)
        if not params:
            try:
                params = await request.json()
            except Exception:
                params = {}
    else:
        params = dict(request.query_params)

    # Process Webhook with 5-step Idempotent Flow
    result = await PaymentService.handle_webhook(
        session=session,
        raw_payload=params,
        background_tasks=background_tasks,
    )

    return JSONResponse(content=result, status_code=200)
