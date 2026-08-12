"""Dependency container — everything is wired once at startup (see app_factory.py)."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver

from ai_service.application.orchestration.supervisor import build_supervisor
from ai_service.application.tools.catalog_tools import build_catalog_tools
from ai_service.application.use_cases.chat_use_case import ChatUseCase
from ai_service.config import Settings
from ai_service.infrastructure.backend.client import BackendHttpClient
from ai_service.infrastructure.llm.factory import build_chat_model


@dataclass
class AppContainer:
    settings: Settings
    backend_client: BackendHttpClient
    chat_use_case: ChatUseCase


def build_container(settings: Settings, checkpointer: BaseCheckpointSaver) -> AppContainer:
    backend_client = BackendHttpClient.build(settings)
    model = build_chat_model(settings)
    tools = build_catalog_tools(backend_client)
    graph = build_supervisor(model, tools, checkpointer)
    chat_use_case = ChatUseCase(graph)

    return AppContainer(settings=settings, backend_client=backend_client, chat_use_case=chat_use_case)
