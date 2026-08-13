"""Dependency wiring — the only place that knows both Protocols and
their concrete implementations.

Build everything once per application lifetime (embedding model load is
slow), never per request.
"""

from typing import Any

import httpx

from agent.supervisor import build_supervisor_agent
from core.config import settings
from infrastructure.llm.factory import build_chat_model
from infrastructure.vector_store.factory import build_embeddings, build_vector_store
from infrastructure.vector_store.qdrant_retriever import QdrantRetriever
from repository.car_repository import CarRepository
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
    """Build the RAG use case wired to the real Qdrant retriever."""
    vector_store = build_vector_store(build_embeddings())
    return RAGService(retriever=QdrantRetriever(vector_store))


def build_supervisor(checkpointer: Any) -> Any:
    """Build the fully wired supervisor agent.

    Args:
        checkpointer (Any): Open checkpointer from core.checkpointer.

    Returns:
        Any: Compiled supervisor graph ready for ainvoke.
    """
    return build_supervisor_agent(
        model=build_chat_model(),
        rag_service=build_rag_service(),
        checkpointer=checkpointer,
    )
