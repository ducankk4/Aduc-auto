"""Data Access Layer (Repository) for the Payments Module.

Executes raw SQLAlchemy 2.0 queries for payment records.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.model import PaymentModel


class PaymentRepository:
    """Repository class encapsulating database access for Payments."""

    @staticmethod
    async def create_payment(session: AsyncSession, payment: PaymentModel) -> PaymentModel:
        """Persist a new Payment entity into the database.

        Args:
            session (AsyncSession): Active database session.
            payment (PaymentModel): Unsaved payment ORM entity.

        Returns:
            PaymentModel: Saved payment entity.
        """
        session.add(payment)
        await session.flush()
        return payment

    @staticmethod
    async def find_by_id(session: AsyncSession, payment_id: UUID) -> Optional[PaymentModel]:
        """Find a payment by its primary key UUID.

        Args:
            session (AsyncSession): Active database session.
            payment_id (UUID): Primary key UUID.

        Returns:
            Optional[PaymentModel]: Payment ORM entity or None.
        """
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .execution_options(populate_existing=True)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_order_id(session: AsyncSession, order_id: UUID) -> Optional[PaymentModel]:
        """Find the latest payment record for a given order.

        Args:
            session (AsyncSession): Active database session.
            order_id (UUID): Order primary key UUID.

        Returns:
            Optional[PaymentModel]: Payment ORM entity or None.
        """
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .order_by(PaymentModel.created_at.desc())
            .execution_options(populate_existing=True)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def find_successful_transaction(
        session: AsyncSession, transaction_code: str
    ) -> Optional[PaymentModel]:
        """Check if a successful payment already exists for a transaction code (Idempotency check).

        Args:
            session (AsyncSession): Active database session.
            transaction_code (str): Gateway transaction reference string.

        Returns:
            Optional[PaymentModel]: Payment ORM entity or None.
        """
        stmt = (
            select(PaymentModel)
            .where(
                PaymentModel.transaction_code == transaction_code,
                PaymentModel.status == "success",
            )
            .execution_options(populate_existing=True)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

