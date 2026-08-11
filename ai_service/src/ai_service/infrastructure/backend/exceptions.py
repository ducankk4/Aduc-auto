"""Exceptions raised by BackendHttpClient, translating backend HTTP/network
failures into ai-service domain exceptions (error-handling-logging.md #3.1).
This is the only module that knows backend's error response shapes.
"""

from __future__ import annotations

from ai_service.domain.exceptions import AiServiceError


class BackendError(AiServiceError):
    """Base for every failure while calling the `backend` API."""

    code = "BACKEND_ERROR"
    status_code = 502


class BackendNotFoundError(BackendError):
    code = "BACKEND_NOT_FOUND"
    status_code = 404


class BackendValidationError(BackendError):
    code = "BACKEND_VALIDATION_ERROR"
    status_code = 422


class BackendUnauthorizedError(BackendError):
    code = "BACKEND_UNAUTHORIZED"
    status_code = 401


class BackendForbiddenError(BackendError):
    code = "BACKEND_FORBIDDEN"
    status_code = 403


class BackendUnavailableError(BackendError):
    code = "BACKEND_UNAVAILABLE"
    status_code = 503
