"""Data Access Layer (Repository) for the Catalog Module.

Executes raw SQLAlchemy 2.0 queries for vehicles, variants, colors, and options.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.model import (
    VehicleModel,
    VariantModel,
    ColorModel,
    OptionModel,
)


class CatalogRepository:
    """Repository class encapsulating database access for Catalog domain models."""

    @staticmethod
    async def find_vehicles(
        session: AsyncSession,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[VehicleModel], int]:
        """Retrieve paginated list of active vehicles.

        Args:
            session (AsyncSession): Active database session.
            page (int): 1-based page number.
            limit (int): Number of items per page.

        Returns:
            Tuple[List[VehicleModel], int]: Pair of vehicle list and total count.
        """
        offset = (page - 1) * limit
        count_stmt = select(func.count(VehicleModel.id)).where(VehicleModel.is_active.is_(True))
        total = (await session.execute(count_stmt)).scalar_one()

        stmt = (
            select(VehicleModel)
            .where(VehicleModel.is_active.is_(True))
            .options(
                selectinload(VehicleModel.variants),
                selectinload(VehicleModel.colors),
            )
            .order_by(VehicleModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def find_by_slug(session: AsyncSession, slug: str) -> Optional[VehicleModel]:
        """Find a vehicle by its unique URL slug, eager loading variants and colors in 1 query.

        Args:
            session (AsyncSession): Active database session.
            slug (str): Vehicle URL slug.

        Returns:
            Optional[VehicleModel]: Vehicle ORM entity or None if not found.
        """
        stmt = (
            select(VehicleModel)
            .where(VehicleModel.slug == slug, VehicleModel.is_active.is_(True))
            .options(
                selectinload(VehicleModel.variants),
                selectinload(VehicleModel.colors),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_id(session: AsyncSession, vehicle_id: UUID) -> Optional[VehicleModel]:
        """Find a vehicle by its unique UUID primary key.

        Args:
            session (AsyncSession): Active database session.
            vehicle_id (UUID): Primary key UUID of the vehicle.

        Returns:
            Optional[VehicleModel]: Vehicle ORM entity or None.
        """
        stmt = (
            select(VehicleModel)
            .where(VehicleModel.id == vehicle_id)
            .options(
                selectinload(VehicleModel.variants),
                selectinload(VehicleModel.colors),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_variant_by_id(session: AsyncSession, variant_id: UUID) -> Optional[VariantModel]:
        """Find a vehicle variant by its primary key UUID.

        Args:
            session (AsyncSession): Active database session.
            variant_id (UUID): Primary key UUID of the variant.

        Returns:
            Optional[VariantModel]: Variant ORM entity or None.
        """
        stmt = select(VariantModel).where(VariantModel.id == variant_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_color_by_id(session: AsyncSession, color_id: UUID) -> Optional[ColorModel]:
        """Find a vehicle color by its primary key UUID.

        Args:
            session (AsyncSession): Active database session.
            color_id (UUID): Primary key UUID of the color.

        Returns:
            Optional[ColorModel]: Color ORM entity or None.
        """
        stmt = select(ColorModel).where(ColorModel.id == color_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_vehicle(session: AsyncSession, vehicle: VehicleModel) -> VehicleModel:
        """Persist a new vehicle entity.

        Args:
            session (AsyncSession): Active database session.
            vehicle (VehicleModel): Unsaved vehicle ORM entity.

        Returns:
            VehicleModel: Saved vehicle ORM entity.
        """
        session.add(vehicle)
        await session.flush()
        return vehicle
