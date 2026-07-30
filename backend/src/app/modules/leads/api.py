"""FastAPI Presentation Layer (Routers) for the Leads Module."""

import time
from collections import defaultdict
from typing import Dict, Any, Optional, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, check_permission
from app.core.exceptions import RateLimitError
from app.core.response import success
from app.modules.leads.constants import MAX_LEADS_PER_MINUTE_PER_IP
from app.modules.leads.schema import (
    LeadCreateSchema,
    LeadStatusUpdateSchema,
    LeadResponseSchema,
)
from app.modules.leads.service import LeadService


DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]

leads_router = APIRouter(prefix="/leads", tags=["Leads"])

# Simple in-memory rate limiting structure: client_ip -> list of request timestamps
_rate_limit_store: Dict[str, list[float]] = defaultdict(list)


def _enforce_rate_limit(request: Request) -> None:
    """Enforce 10 requests per minute rate limit per client IP.

    Args:

        request (Request): Active HTTP request object.

    Raises:
        RateLimitError: If IP exceeds MAX_LEADS_PER_MINUTE_PER_IP within 60 seconds.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    timestamps = _rate_limit_store[client_ip]

    # Retain timestamps within the last 60 seconds
    valid_timestamps = [ts for ts in timestamps if now - ts < 60]
    _rate_limit_store[client_ip] = valid_timestamps

    if len(valid_timestamps) >= MAX_LEADS_PER_MINUTE_PER_IP:
        raise RateLimitError("Gửi yêu cầu quá nhanh. Bạn chỉ được phép gửi tối đa 10 yêu cầu/phút.")

    _rate_limit_store[client_ip].append(now)


@leads_router.post("", dependencies=[Depends(_enforce_rate_limit)])
async def submit_lead(
    payload: LeadCreateSchema,
    background_tasks: BackgroundTasks,
    session: DBSession,
):
    """Public endpoint to submit customer test drive / lead request (rate limited 10 req/min/IP)."""
    lead = await LeadService.submit_lead(
        session=session,
        vehicle_id=payload.vehicle_id,
        customer_name=payload.customer_name,
        phone=payload.phone,
        email=payload.email,
        showroom_pref=payload.showroom_pref,
        background_tasks=background_tasks,
    )
    data = LeadResponseSchema.model_validate(lead).model_dump(mode="json")
    return success(data=data, status_code=201)


@leads_router.get("", dependencies=[Depends(check_permission("leads", "read"))])
async def list_leads(
    session: DBSession,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Admin endpoint to list customer leads with optional status filtering."""
    leads, total = await LeadService.list_leads(
        session=session, status_filter=status, page=page, limit=limit
    )
    data = [LeadResponseSchema.model_validate(l).model_dump(mode="json") for l in leads]
    return success(data=data, meta={"page": page, "limit": limit, "total": total})


@leads_router.patch(
    "/{lead_id}/status",
    dependencies=[Depends(check_permission("leads", "write"))],
)
async def update_lead_status(
    lead_id: UUID,
    payload: LeadStatusUpdateSchema,
    current_user: CurrentUser,
    session: DBSession,
):
    """Admin endpoint to update lead status lifecycle."""
    user_id = UUID(current_user["sub"])
    lead = await LeadService.update_lead_status(
        session=session,
        user_id=user_id,
        lead_id=lead_id,
        new_status=payload.status,
    )
    data = LeadResponseSchema.model_validate(lead).model_dump(mode="json")
    return success(data=data)
