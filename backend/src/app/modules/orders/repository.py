"""Data Access Layer (Repository) for the Orders Module.

Executes raw SQLAlchemy 2.0 queries for order and status history records.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.orders.model import OrderModel, OrderStatusHistory


class OrderRepository:
    """Repository class encapsulating database access for Orders."""

    @staticmethod
    async def create_order(session: AsyncSession, order: OrderModel) -> OrderModel:
        """Persist a new Order entity into the database.

        Args:
            session (AsyncSession): Active database session.
            order (OrderModel): Unsaved order ORM entity.

        Returns:
            OrderModel: Saved order ORM entity.
        """
        session.add(order)
        await session.flush()
        return order

    @staticmethod
    async def create_status_history(
        session: AsyncSession, history_entry: OrderStatusHistory
    ) -> OrderStatusHistory:
        """Persist an order status audit history entry.

        Args:
            session (AsyncSession): Active database session.
            history_entry (OrderStatusHistory): Status history entry.

        Returns:
            OrderStatusHistory: Saved status history entity.
        """
        session.add(history_entry)
        await session.flush()
        return history_entry

    @staticmethod
    async def find_by_id(session: AsyncSession, order_id: UUID) -> Optional[OrderModel]:
        """Find an order by its unique primary key UUID.

        Args:
            session (AsyncSession): Active database session.
            order_id (UUID): Primary key UUID.

        Returns:
            Optional[OrderModel]: Order ORM entity or None.
        """
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(selectinload(OrderModel.history))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_code(session: AsyncSession, order_code: str) -> Optional[OrderModel]:
        """Find an order by its unique business order code string.

        Args:
            session (AsyncSession): Active database session.
            order_code (str): Business order code identifier (e.g. 'ORD-20260730-A1B2C3').

        Returns:
            Optional[OrderModel]: Order ORM entity or None.
        """
        stmt = (
            select(OrderModel)
            .where(OrderModel.order_code == order_code)
            .options(selectinload(OrderModel.history))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_user_orders(
        session: AsyncSession,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[OrderModel], int]:
        """Retrieve paginated orders belonging to a specific customer user.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): Customer user UUID.
            page (int): 1-based page number.
            limit (int): Items per page.

        Returns:
            Tuple[List[OrderModel], int]: Orders list and total count.
        """
        offset = (page - 1) * limit
        count_stmt = select(func.count(OrderModel.id)).where(OrderModel.user_id == user_id)
        total = (await session.execute(count_stmt)).scalar_one()

        stmt = (
            select(OrderModel)
            .where(OrderModel.user_id == user_id)
            .options(selectinload(OrderModel.history))
            .order_by(OrderModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def find_all_orders(
        session: AsyncSession,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[OrderModel], int]:
        """Retrieve paginated list of all orders with optional status filter for admin.

        Args:
            session (AsyncSession): Active database session.
            status_filter (Optional[str]): Optional status filter string.
            page (int): 1-based page number.
            limit (int): Items per page.

        Returns:
            Tuple[List[OrderModel], int]: Orders list and total count.
        """
        offset = (page - 1) * limit
        count_stmt = select(func.count(OrderModel.id))
        stmt = select(OrderModel).options(selectinload(OrderModel.history))

        if status_filter:
            count_stmt = count_stmt.where(OrderModel.status == status_filter)
            stmt = stmt.where(OrderModel.status == status_filter)

        total = (await session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(OrderModel.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all()), total
