"""FastAPI Presentation Layer (Routers) for the Orders Module."""
from typing import Dict, Any, Optional, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, check_permission, security_scheme
from app.core.response import success
from app.core.security import decode_token
from app.modules.orders.schema import (
    OrderCreateSchema,
    OrderUpdateStatusSchema,
    OrderResponseSchema,
)
from app.modules.orders.service import OrderService


DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]

orders_router = APIRouter(prefix="/orders", tags=["Orders"])
admin_orders_router = APIRouter(prefix="/admin/orders", tags=["Admin Orders"])


@orders_router.post("")
async def create_order(
    payload: OrderCreateSchema,
    session: DBSession,
    credentials=Depends(security_scheme),
):
    """Customer endpoint to place a car deposit order."""
    user_id: Optional[UUID] = None
    if credentials and credentials.credentials:
        try:
            token_data = decode_token(credentials.credentials)
            if token_data.get("sub"):
                user_id = UUID(token_data["sub"])
        except Exception:
            pass  # Allow guest order creation if token invalid/absent

    order = await OrderService.create(
        session=session,
        user_id=user_id,
        variant_id=payload.variant_id,
        color_id=payload.color_id,
        customer_name=payload.customer_name,
        phone=payload.phone,
        email=payload.email,
        id_card=payload.id_card,
    )
    data = OrderResponseSchema.model_validate(order).model_dump(mode="json")
    return success(data=data, status_code=201)


@orders_router.get("/me")
async def list_my_orders(
    current_user: CurrentUser,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Customer endpoint to view personal deposit orders."""
    user_id = UUID(current_user["sub"])
    orders, total = await OrderService.list_user_orders(session, user_id=user_id, page=page, limit=limit)
    data = [OrderResponseSchema.model_validate(o).model_dump(mode="json") for o in orders]
    return success(data=data, meta={"page": page, "limit": limit, "total": total})


@orders_router.get("/{order_code}")
async def get_order_by_code(
    order_code: str,
    current_user: CurrentUser,
    session: DBSession,
):
    """Customer endpoint to view detailed order information by order code."""
    user_id = UUID(current_user["sub"])
    # System admin can view any order, standard users can only view their own
    is_admin = current_user.get("role") == "admin"
    check_user_id = None if is_admin else user_id

    order = await OrderService.get_by_code(session, order_code, user_id=check_user_id)
    data = OrderResponseSchema.model_validate(order).model_dump(mode="json")
    return success(data=data)


@admin_orders_router.get("", dependencies=[Depends(check_permission("orders", "read"))])
async def list_all_orders(
    session: DBSession,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),

):
    """Admin endpoint to list all customer deposit orders."""
    orders, total = await OrderService.list_all_orders(
        session=session, status_filter=status, page=page, limit=limit
    )
    data = [OrderResponseSchema.model_validate(o).model_dump(mode="json") for o in orders]
    return success(data=data, meta={"page": page, "limit": limit, "total": total})


@admin_orders_router.patch(
    "/{order_id}/status",
    dependencies=[Depends(check_permission("orders", "update_status"))],
)
async def admin_update_order_status(
    order_id: UUID,
    payload: OrderUpdateStatusSchema,
    current_user: CurrentUser,
    session: DBSession,
):
    """Admin endpoint to transition order status according to state machine rules."""
    user_id = UUID(current_user["sub"])
    order = await OrderService.update_status(
        session=session,
        order_id=order_id,
        new_status=payload.status,
        changed_by=user_id,
        note=payload.note,
    )
    data = OrderResponseSchema.model_validate(order).model_dump(mode="json")
    return success(data=data)
