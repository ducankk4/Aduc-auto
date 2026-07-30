"""Business Logic & Public Service Interface for the Catalog Module.

Exposes public methods for catalog management and inter-module service communication.
"""

from typing import Tuple, List, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log as audit_log
from app.core.exceptions import NotFoundError, ConflictError
from app.modules.catalog.model import VehicleModel, VariantModel, ColorModel
from app.modules.catalog.repository import CatalogRepository


class CatalogService:
    """Catalog Domain Service encapsulating public methods for vehicle management."""

    @staticmethod
    async def list_vehicles(
        session: AsyncSession,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[VehicleModel], int]:
        """Fetch paginated active vehicle catalog list.

        Args:
            session (AsyncSession): Active database session.
            page (int): 1-based page number.
            limit (int): Maximum records per page.

        Returns:
            Tuple[List[VehicleModel], int]: Vehicles list and total items count.
        """
        return await CatalogRepository.find_vehicles(session, page=page, limit=limit)

    @staticmethod
    async def get_by_slug(session: AsyncSession, slug: str) -> VehicleModel:
        """Retrieve detailed vehicle information by URL slug (eager loads variants & colors in 1 query).

        Args:
            session (AsyncSession): Active database session.
            slug (str): Unique vehicle URL slug.

        Returns:
            VehicleModel: Found vehicle entity.

        Raises:
            NotFoundError: If no vehicle matches the given slug.
        """
        vehicle = await CatalogRepository.find_by_slug(session, slug)
        if not vehicle:
            raise NotFoundError(f"Không tìm thấy mẫu xe với slug: '{slug}'")
        return vehicle

    @staticmethod
    async def get_by_id(session: AsyncSession, vehicle_id: UUID) -> VehicleModel:
        """Retrieve detailed vehicle entity by UUID primary key (used by external modules like leads/orders).

        Args:
            session (AsyncSession): Active database session.
            vehicle_id (UUID): Unique vehicle UUID.

        Returns:
            VehicleModel: Found vehicle entity.

        Raises:
            NotFoundError: If no vehicle matches the given ID.
        """
        vehicle = await CatalogRepository.find_by_id(session, vehicle_id)
        if not vehicle:
            raise NotFoundError(f"Không tìm thấy mẫu xe với ID: '{vehicle_id}'")
        return vehicle

    @staticmethod
    async def get_variant(session: AsyncSession, variant_id: UUID) -> VariantModel:
        """Public interface for orders/service to retrieve and validate vehicle variant.

        Args:
            session (AsyncSession): Active database session.
            variant_id (UUID): Variant primary key UUID.

        Returns:
            VariantModel: Found variant entity.

        Raises:
            NotFoundError: If no variant matches the given ID.
        """
        variant = await CatalogRepository.find_variant_by_id(session, variant_id)
        if not variant:
            raise NotFoundError(f"Không tìm thấy phiên bản xe (variant) với ID: '{variant_id}'")
        return variant

    @staticmethod
    async def get_color(session: AsyncSession, color_id: UUID) -> ColorModel:
        """Public interface for orders/service to retrieve and validate vehicle color.

        Args:
            session (AsyncSession): Active database session.
            color_id (UUID): Color primary key UUID.

        Returns:
            ColorModel: Found color entity.

        Raises:
            NotFoundError: If no color matches the given ID.
        """
        color = await CatalogRepository.find_color_by_id(session, color_id)
        if not color:
            raise NotFoundError(f"Không tìm thấy tùy chọn màu xe (color) với ID: '{color_id}'")
        return color

    @staticmethod
    async def admin_create_vehicle(
        session: AsyncSession,
        user_id: UUID,
        **data: Any,
    ) -> VehicleModel:
        """Admin operation to create a new vehicle product with variants and colors.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): Admin user UUID performing the creation.
            **data: Vehicle fields and nested variants/colors lists.

        Returns:
            VehicleModel: Created vehicle entity.

        Raises:
            ConflictError: If a vehicle with the same slug already exists.
        """
        existing = await CatalogRepository.find_by_slug(session, data["slug"])
        if existing:
            raise ConflictError(f"Slug xe '{data['slug']}' đã tồn tại trong hệ thống")

        variants_data = data.pop("variants", [])
        colors_data = data.pop("colors", [])

        vehicle = VehicleModel(**data)
        for var_data in variants_data:
            if isinstance(var_data, dict):
                vehicle.variants.append(VariantModel(**var_data))
            else:
                vehicle.variants.append(VariantModel(**var_data.model_dump()))

        for col_data in colors_data:
            if isinstance(col_data, dict):
                vehicle.colors.append(ColorModel(**col_data))
            else:
                vehicle.colors.append(ColorModel(**col_data.model_dump()))

        created_vehicle = await CatalogRepository.create_vehicle(session, vehicle)

        # Audit log creation event
        await audit_log(
            session=session,
            user_id=user_id,
            action="catalog.vehicle_created",
            resource="catalog",
            resource_id=created_vehicle.id,
            payload={"name": created_vehicle.name, "slug": created_vehicle.slug},
        )

        return created_vehicle

    @staticmethod
    async def admin_update_vehicle(
        session: AsyncSession,
        user_id: UUID,
        vehicle_id: UUID,
        **data: Any,
    ) -> VehicleModel:
        """Admin operation to update vehicle attributes.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): Admin user UUID performing update.
            vehicle_id (UUID): Target vehicle UUID.
            **data: Fields to update.

        Returns:
            VehicleModel: Updated vehicle entity.
        """
        vehicle = await CatalogService.get_by_id(session, vehicle_id)

        update_fields = {k: v for k, v in data.items() if v is not None}
        for field, value in update_fields.items():
            setattr(vehicle, field, value)

        await session.flush()

        # Audit log update event
        await audit_log(
            session=session,
            user_id=user_id,
            action="catalog.vehicle_updated",
            resource="catalog",
            resource_id=vehicle.id,
            payload=update_fields,
        )

        return vehicle
