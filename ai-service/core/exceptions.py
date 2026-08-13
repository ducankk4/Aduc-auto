"""Framework-free exception hierarchy for ai-service.

Only api/ is allowed to map these exceptions to HTTP status codes
(in a centralized exception handler). Every other layer raises and
catches these types directly.
"""


class AIServiceError(Exception):
    """Base exception for every error raised inside ai-service."""

    code: str = "AI_SERVICE_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DomainError(AIServiceError):
    """Business rule violation detected in the domain layer."""

    code = "DOMAIN_ERROR"


class NotFoundError(AIServiceError):
    """A requested resource does not exist."""

    code = "NOT_FOUND"


class InfrastructureError(AIServiceError):
    """An external dependency (backend API, LLM, vector store, DB) failed."""

    code = "INFRASTRUCTURE_ERROR"


class ApprovalRejectedError(AIServiceError):
    """A sensitive tool call was rejected by the human approver."""

    code = "APPROVAL_REJECTED"
