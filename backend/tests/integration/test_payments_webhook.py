"""Integration Test for Payments Webhook Endpoint (Full end-to-end HTTP response)."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_payments_webhook_always_returns_200():
    """Verify POST /api/v1/payments/webhook ALWAYS returns HTTP 200."""
    webhook_payload = {
        "vnp_Amount": "5000000000",
        "vnp_ResponseCode": "00",
        "vnp_TransactionNo": "999888777",
        "vnp_TxnRef": "ORD-20260730-INT01",
        "vnp_SecureHash": "invalid_hash_should_still_return_200",
    }

    with patch("app.modules.payments.service.PaymentService.handle_webhook", new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = {"RspCode": "00", "Message": "Confirm Success"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/payments/webhook", data=webhook_payload)

            assert response.status_code == 200
            json_resp = response.json()
            assert json_resp["RspCode"] == "00"
            assert json_resp["Message"] == "Confirm Success"
