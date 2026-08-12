"""Dependency container — everything is wired once at startup (see app_factory.py)."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver

from ai_service.application.orchestration.subagents.catalog_advisor import (
    build_catalog_advisor_graph,
    build_catalog_advisor_tool,
)
from ai_service.application.orchestration.supervisor import build_supervisor
from ai_service.application.tools.catalog_tools import build_catalog_tools
from ai_service.application.tools.rag_tools import build_rag_tools
from ai_service.application.use_cases.chat_use_case import ChatUseCase
from ai_service.config import Settings
from ai_service.infrastructure.backend.client import BackendHttpClient
from ai_service.infrastructure.llm.factory import build_chat_model
from ai_service.infrastructure.rag.embedding import SentenceTransformerEmbedder
from ai_service.infrastructure.rag.qdrant_retriever import QdrantRetriever


@dataclass
class AppContainer:
    settings: Settings
    backend_client: BackendHttpClient
    retriever: QdrantRetriever
    chat_use_case: ChatUseCase


async def build_container(settings: Settings, checkpointer: BaseCheckpointSaver) -> AppContainer:
    backend_client = BackendHttpClient.build(settings)
    model = build_chat_model(settings)

    embedder = SentenceTransformerEmbedder.build(settings)
    retriever = await QdrantRetriever.build(settings, embedder)

    catalog_tools = build_catalog_tools(backend_client)
    rag_tools = build_rag_tools(retriever)
    catalog_advisor_graph = build_catalog_advisor_graph(model, catalog_tools + rag_tools)
    catalog_advisor_tool = build_catalog_advisor_tool(catalog_advisor_graph)

    graph = build_supervisor(model, [catalog_advisor_tool], checkpointer)
    chat_use_case = ChatUseCase(graph)

    return AppContainer(
        settings=settings,
        backend_client=backend_client,
        retriever=retriever,
        chat_use_case=chat_use_case,
    )
