"""HTTP client for the `backend` FastAPI service. The only module in
ai-service that imports httpx or knows about backend's
{success,data,meta,error} response envelope.

Backend's global exception handler only wraps `AppError` subclasses
(backend/src/app/main.py) — plain `HTTPException` or Pydantic validation
errors fall through to FastAPI's default `{"detail": ...}` shape instead of
the envelope. `_extract_error_message` accounts for both.
"""

from __future__ import annotations

from typing import Any

import httpx

from ai_service.application.dto.vehicle import VehicleSummaryDTO
from ai_service.application.ports.backend_port import BackendPort
from ai_service.config import Settings
from ai_service.infrastructure.backend.exceptions import (
    BackendError,
    BackendForbiddenError,
    BackendNotFoundError,
    BackendUnauthorizedError,
    BackendUnavailableError,
    BackendValidationError,
)
from ai_service.infrastructure.backend.schemas import VehicleSummarySchema

_STATUS_TO_ERROR: dict[int, type[BackendError]] = {
    400: BackendValidationError,
    401: BackendUnauthorizedError,
    403: BackendForbiddenError,
    404: BackendNotFoundError,
    422: BackendValidationError,
}


class BackendHttpClient(BackendPort):
    """Typed async client for backend's public/admin REST API."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    @classmethod
    def build(cls, settings: Settings) -> "BackendHttpClient":
        http_client = httpx.AsyncClient(
            base_url=settings.backend_base_url,
            timeout=settings.backend_timeout_seconds,
        )
        return cls(http_client)

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def list_vehicles(self, page: int = 1, limit: int = 20) -> list[VehicleSummaryDTO]:
        payload = await self._get("/catalog/vehicles", params={"page": page, "limit": limit})
        vehicles = [VehicleSummarySchema.model_validate(item) for item in payload or []]
        return [
            VehicleSummaryDTO(
                id=v.id,
                name=v.name,
                slug=v.slug,
                category=v.category,
                base_price=v.base_price,
                is_active=v.is_active,
            )
            for v in vehicles
        ]

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        try:
            response = await self._http_client.get(path, params=params)
        except httpx.TimeoutException as err:
            raise BackendUnavailableError("Backend response timed out, please try again.") from err
        except httpx.RequestError as err:
            raise BackendUnavailableError("Unable to connect to backend.") from err

        if response.status_code >= 500:
            raise BackendUnavailableError("Backend is currently unavailable, please try again later.")

        if response.is_error:
            raise self._build_error(response)

        body = response.json()
        return body.get("data") if isinstance(body, dict) else body

    def _build_error(self, response: httpx.Response) -> BackendError:
        message = self._extract_error_message(response)
        error_cls = _STATUS_TO_ERROR.get(response.status_code, BackendError)
        return error_cls(message)

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text or "Backend returned an unknown error."

        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])
            detail = body.get("detail")
            if isinstance(detail, str):
                return detail
            if isinstance(detail, list) and detail:
                return "; ".join(str(item.get("msg", item)) for item in detail)
        return "Backend returned an unknown error."
