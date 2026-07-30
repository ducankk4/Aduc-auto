"""Unit Tests for Leads Service (Submit Lead, Update Status)."""

from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import pytest

from app.core.exceptions import NotFoundError
from app.modules.leads.model import LeadModel
from app.modules.leads.service import LeadService


@pytest.mark.asyncio
async def test_submit_lead_success():
    """Verify submit_lead retrieves vehicle via catalog service and inserts new lead."""
    session_mock = AsyncMock()
    fake_vehicle_id = uuid4()
    fake_lead_id = uuid4()

    mock_vehicle = MagicMock()
    mock_vehicle.id = fake_vehicle_id
    mock_vehicle.name = "Aduc Lux SUV"

    mock_created_lead = LeadModel(
        id=fake_lead_id,
        vehicle_id=fake_vehicle_id,
        customer_name="Trần Văn Test",
        phone="0912345678",
        email="test@example.com",
        showroom_pref="Hà Nội",
        status="new",
    )

    with patch("app.modules.catalog.service.CatalogService.get_by_id", return_value=mock_vehicle) as mock_get_vehicle, \
         patch("app.modules.leads.repository.LeadRepository.create_lead", return_value=mock_created_lead) as mock_create_lead, \
         patch("app.modules.leads.service.send_lead_notification", new_callable=AsyncMock):

        lead = await LeadService.submit_lead(
            session=session_mock,
            vehicle_id=fake_vehicle_id,
            customer_name="Trần Văn Test",
            phone="0912345678",
            email="test@example.com",
            showroom_pref="Hà Nội",
        )

        mock_get_vehicle.assert_called_once_with(session_mock, fake_vehicle_id)
        assert lead.status == "new"
        assert lead.customer_name == "Trần Văn Test"


@pytest.mark.asyncio
async def test_submit_lead_invalid_vehicle_raises_not_found():
    """Verify submit_lead raises NotFoundError when vehicle does not exist."""
    session_mock = AsyncMock()
    fake_vehicle_id = uuid4()

    with patch("app.modules.catalog.service.CatalogService.get_by_id", side_effect=NotFoundError("Vehicle not found")):
        with pytest.raises(NotFoundError):
            await LeadService.submit_lead(
                session=session_mock,
                vehicle_id=fake_vehicle_id,
                customer_name="Trần Văn Test",
                phone="0912345678",
                email="test@example.com",
            )
