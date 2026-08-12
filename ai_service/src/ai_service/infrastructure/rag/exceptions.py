"""Exceptions raised by RAG infrastructure adapters (embedding + vector
store), translating their failures into ai-service domain exceptions
(error-handling-logging.md #3.1).
"""

from __future__ import annotations

from ai_service.domain.exceptions import AiServiceError


class RetrieverUnavailableError(AiServiceError):
    """The vector store (Qdrant) is unreachable or returned an unexpected
    error while embedding, searching, or indexing.
    """

    code = "RETRIEVER_UNAVAILABLE"
    status_code = 503
