"""Data Access Layer (Repository) for the Leads Module.

Executes raw SQLAlchemy 2.0 queries for leads database operations.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.leads.model import LeadModel


class LeadRepository:
    """Repository class encapsulating database access for Lead entities."""

    @staticmethod
    async def create_lead(session: AsyncSession, lead: LeadModel) -> LeadModel:
        """Persist a new Lead entity into the database.

        Args:
            session (AsyncSession): Active database session.
            lead (LeadModel): Unsaved lead ORM entity.

        Returns:
            LeadModel: Saved lead ORM entity.
        """
        session.add(lead)
        await session.flush()
        return lead

    @staticmethod
    async def find_by_id(session: AsyncSession, lead_id: UUID) -> Optional[LeadModel]:
        """Find a lead by its primary key UUID.

        Args:
            session (AsyncSession): Active database session.
            lead_id (UUID): Lead primary key UUID.

        Returns:
            Optional[LeadModel]: Lead ORM entity or None.
        """
        stmt = (
            select(LeadModel)
            .where(LeadModel.id == lead_id)
            .execution_options(populate_existing=True)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_leads(
        session: AsyncSession,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[LeadModel], int]:
        """Retrieve paginated leads with optional status filter.

        Args:
            session (AsyncSession): Active database session.
            status_filter (Optional[str]): Filter by lead status.
            page (int): 1-based page number.
            limit (int): Items per page.

        Returns:
            Tuple[List[LeadModel], int]: Lead list and total item count.
        """
        offset = (page - 1) * limit
        count_stmt = select(func.count(LeadModel.id))
        stmt = select(LeadModel).execution_options(populate_existing=True)

        if status_filter:
            count_stmt = count_stmt.where(LeadModel.status == status_filter)
            stmt = stmt.where(LeadModel.status == status_filter)

        total = (await session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(LeadModel.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all()), total

