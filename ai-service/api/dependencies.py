"""Dependency wiring — the only place that knows both abstract contracts
and their concrete implementations.

Build everything once per application lifetime (embedding model load is
slow), never per request.
"""

from typing import Any

import httpx

from agent.subagent.data_ops import build_data_ops_subagent
from agent.supervisor import build_supervisor_agent
from core.config import settings
from infrastructure.llm.groq import build_chat_model
from infrastructure.vector_store.qdrant import (
    QdrantDocumentRepository,
    build_embeddings,
    build_vector_store,
)
from repository.booking_repository import BookingRepository
from repository.car_repository import CarRepository
from repository.message_repository import SqliteMessageRepository
from services.booking_service import BookingService
from services.car_service import CarService
from services.message_service import MessageService
from services.rag_service import RAGService


def build_backend_client() -> httpx.AsyncClient:
    """Build the shared httpx client pointed at the backend API."""
    return httpx.AsyncClient(
        base_url=settings.BACKEND_API_URL,
        timeout=settings.BACKEND_API_TIMEOUT_SECONDS,
    )


def build_car_repository(client: httpx.AsyncClient) -> CarRepository:
    """Build the vehicle repository on top of the shared backend client."""
    return CarRepository(client=client)


def build_rag_service() -> RAGService:
    """Build the RAG use case wired to the real Qdrant document repository."""
    vector_store = build_vector_store(build_embeddings())
    return RAGService(document_repository=QdrantDocumentRepository(vector_store))


async def build_message_service() -> MessageService:
    """Build the conversation-history use case and create its table if missing."""
    repository = SqliteMessageRepository(db_path=settings.CONVERSATION_DB_PATH)
    await repository.init()
    return MessageService(message_repository=repository)


def build_supervisor(checkpointer: Any) -> Any:
    """Build the fully wired supervisor agent.

    Args:
        checkpointer (Any): Open checkpointer from agent.checkpointer.

    Returns:
        Any: Compiled supervisor graph ready for ainvoke.
    """
    client = build_backend_client()
    car_repository = build_car_repository(client)
    car_service = CarService(car_repository=car_repository)
    booking_service = BookingService(
        booking_repository=BookingRepository(client=client),
        car_repository=car_repository,
    )
    return build_supervisor_agent(
        model=build_chat_model(),
        rag_service=build_rag_service(),
        subagents=[build_data_ops_subagent(car_service, booking_service)],
        checkpointer=checkpointer,
    )
