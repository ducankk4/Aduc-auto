"""Supervisor agent built on DeepAgents.

This is the ONLY module that imports deepagents. The model, services, and
checkpointer are injected from api/ (wiring) so this layer never touches
infrastructure directly.
"""

from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from loguru import logger

from agent.prompt.prompts import DATA_OPS_STUB_PROMPT, SUPERVISOR_SYSTEM_PROMPT
from agent.tools.rag import build_rag_search_tool
from services.rag_service import RAGService

_DATA_OPS_STUB = {
    "name": "data-ops",
    "description": (
        "Tra cứu và thao tác dữ liệu xe: danh sách xe, giá, phiên bản, màu, "
        "đặt lịch lái thử. (Hiện là stub — Phase 2 sẽ gắn tool thật.)"
    ),
    "system_prompt": DATA_OPS_STUB_PROMPT,
    "tools": [],
}


def build_supervisor_agent(
    model: BaseChatModel,
    rag_service: RAGService,
    checkpointer: Any,
) -> Any:
    """Build the supervisor deep agent with RAG tool and subagents.

    Args:
        model (BaseChatModel): Chat model from infrastructure/llm factory.
        rag_service (RAGService): Retrieval use case for the rag_search tool.
        checkpointer (Any): LangGraph checkpointer (SQLite saver) so the
            graph state persists across interrupts.

    Returns:
        Any: Compiled agent graph, invokable with {"messages": [...]}.
    """
    logger.info("Building supervisor agent [subagents={}]", [_DATA_OPS_STUB["name"]])
    return create_deep_agent(
        model=model,
        tools=[build_rag_search_tool(rag_service)],
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        # subagents=[_DATA_OPS_STUB],
        checkpointer=checkpointer,
    )
