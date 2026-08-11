"""Unit tests for BackendHttpClient's error-mapping logic — the boundary
that must handle both backend's {success,error} envelope and FastAPI's
default {"detail": ...} shape (see infrastructure/backend/client.py).
"""

from __future__ import annotations

import httpx
import pytest

from ai_service.infrastructure.backend.client import BackendHttpClient
from ai_service.infrastructure.backend.exceptions import (
    BackendNotFoundError,
    BackendUnavailableError,
    BackendValidationError,
)


async def test_maps_enveloped_backend_error_to_typed_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"success": False, "error": {"code": "NOT_FOUND", "message": "Không tìm thấy xe"}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend.test")
    client = BackendHttpClient(http_client)

    with pytest.raises(BackendNotFoundError) as exc_info:
        await client.list_vehicles()
    assert exc_info.value.message == "Không tìm thấy xe"

    await http_client.aclose()


async def test_maps_unwrapped_detail_error_to_typed_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": [{"loc": ["query", "page"], "msg": "invalid page"}]},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend.test")
    client = BackendHttpClient(http_client)

    with pytest.raises(BackendValidationError) as exc_info:
        await client.list_vehicles()
    assert "invalid page" in exc_info.value.message

    await http_client.aclose()


async def test_maps_network_failure_to_unavailable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend.test")
    client = BackendHttpClient(http_client)

    with pytest.raises(BackendUnavailableError):
        await client.list_vehicles()

    await http_client.aclose()
