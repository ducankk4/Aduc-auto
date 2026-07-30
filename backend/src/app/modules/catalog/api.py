"""FastAPI Presentation Layer (Routers) for the Catalog Module."""

from typing import Dict, Any, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, check_permission
from app.core.response import success
from app.modules.catalog.schema import (
    VehicleCreateSchema,
    VehicleUpdateSchema,
    VehicleResponseSchema,
)
from app.modules.catalog.service import CatalogService

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]

catalog_router = APIRouter(prefix="/catalog", tags=["Catalog"])


@catalog_router.get("/vehicles")
async def list_vehicles(
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),

):
    """Public endpoint to list vehicles with pagination."""
    vehicles, total = await CatalogService.list_vehicles(session, page=page, limit=limit)
    data = [VehicleResponseSchema.model_validate(v).model_dump(mode="json") for v in vehicles]
    return success(data=data, meta={"page": page, "limit": limit, "total": total})


@catalog_router.get("/vehicles/{slug}")
async def get_vehicle_by_slug(
    slug: str,
    session: DBSession,
):
    """Public endpoint to retrieve vehicle details by unique URL slug."""
    vehicle = await CatalogService.get_by_slug(session, slug)
    data = VehicleResponseSchema.model_validate(vehicle).model_dump(mode="json")
    return success(data=data)


@catalog_router.post(
    "/vehicles",
    dependencies=[Depends(check_permission("catalog", "write"))],
)
async def admin_create_vehicle(
    payload: VehicleCreateSchema,
    current_user: CurrentUser,
    session: DBSession,
):
    """Admin endpoint to create a new vehicle product."""
    user_id = UUID(current_user["sub"])
    vehicle = await CatalogService.admin_create_vehicle(
        session=session,
        user_id=user_id,
        **payload.model_dump(),
    )
    data = VehicleResponseSchema.model_validate(vehicle).model_dump(mode="json")
    return success(data=data, status_code=201)


@catalog_router.put(
    "/vehicles/{vehicle_id}",
    dependencies=[Depends(check_permission("catalog", "write"))],
)
async def admin_update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdateSchema,
    current_user: CurrentUser,
    session: DBSession,
):
    """Admin endpoint to update vehicle details."""
    user_id = UUID(current_user["sub"])
    vehicle = await CatalogService.admin_update_vehicle(
        session=session,
        user_id=user_id,
        vehicle_id=vehicle_id,
        **payload.model_dump(),
    )
    data = VehicleResponseSchema.model_validate(vehicle).model_dump(mode="json")
    return success(data=data)
