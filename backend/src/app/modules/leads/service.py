"""Business Logic & Service Interface for the Leads Module.

Orchestrates lead creation, status updates, cross-module calls to catalog, and audit logging.
"""

import asyncio
from typing import Tuple, List, Optional
from uuid import UUID
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log as audit_log
from app.core.exceptions import NotFoundError
from app.modules.catalog.service import CatalogService
from app.modules.leads.model import LeadModel
from app.modules.leads.repository import LeadRepository
from app.workers.email import send_lead_notification


class LeadService:
    """Lead Domain Service encapsulating lead submission and management logic."""

    @staticmethod
    async def submit_lead(
        session: AsyncSession,
        vehicle_id: UUID,
        customer_name: str,
        phone: str,
        email: str,
        showroom_pref: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> LeadModel:
        """Submit a new customer lead / test drive request.

        Args:
            session (AsyncSession): Active database session.
            vehicle_id (UUID): Target vehicle UUID.
            customer_name (str): Customer full name.
            phone (str): Contact phone number.
            email (str): Contact email address.
            showroom_pref (Optional[str]): Preferred showroom branch.
            background_tasks (Optional[BackgroundTasks]): FastAPI background task context.

        Returns:
            LeadModel: Created Lead ORM entity.

        Raises:
            NotFoundError: If vehicle_id is invalid or vehicle does not exist.
        """
        # 1. Validate vehicle existence via catalog.service (NO import of catalog models/repository)
        vehicle = await CatalogService.get_by_id(session, vehicle_id)

        # 2. Insert LeadModel with default status="new"
        lead = LeadModel(
            vehicle_id=vehicle.id,
            customer_name=customer_name,
            phone=phone,
            email=email,
            showroom_pref=showroom_pref,
            status="new",
        )
        created_lead = await LeadRepository.create_lead(session, lead)

        # 3. Trigger background email notification
        if background_tasks:
            background_tasks.add_task(
                send_lead_notification,
                lead_id=created_lead.id,
                customer_name=customer_name,
                email=email,
                phone=phone,
                vehicle_name=vehicle.name,
            )
        else:
            asyncio.create_task(
                send_lead_notification(
                    lead_id=created_lead.id,
                    customer_name=customer_name,
                    email=email,
                    phone=phone,
                    vehicle_name=vehicle.name,
                )
            )

        return created_lead

    @staticmethod
    async def list_leads(
        session: AsyncSession,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[LeadModel], int]:
        """Fetch paginated leads with optional status filter.

        Args:
            session (AsyncSession): Active database session.
            status_filter (Optional[str]): Filter lead status.
            page (int): 1-based page number.
            limit (int): Items per page.

        Returns:
            Tuple[List[LeadModel], int]: Lead list and total count.
        """
        return await LeadRepository.find_leads(
            session, status_filter=status_filter, page=page, limit=limit
        )

    @staticmethod
    async def update_lead_status(
        session: AsyncSession,
        user_id: UUID,
        lead_id: UUID,
        new_status: str,
    ) -> LeadModel:
        """Update lead status lifecycle state.

        Args:
            session (AsyncSession): Active database session.
            user_id (UUID): Admin/Sale user UUID performing status update.
            lead_id (UUID): Lead primary key UUID.
            new_status (str): Target status value.

        Returns:
            LeadModel: Updated Lead ORM entity.

        Raises:
            NotFoundError: If lead with given ID does not exist.
        """
        lead = await LeadRepository.find_by_id(session, lead_id)
        if not lead:
            raise NotFoundError(f"Không tìm thấy Lead với ID: '{lead_id}'")

        lead.status = new_status
        await session.flush()

        # Audit log status update
        await audit_log(
            session=session,
            user_id=user_id,
            action="lead.status_updated",
            resource="leads",
            resource_id=lead.id,
            payload={"status": new_status},
        )

        return lead
