"""Supervisor agent built on DeepAgents.

This is the ONLY module that imports deepagents. The model, services,
subagent specs, and checkpointer are injected from api/ (wiring) so this
layer never touches infrastructure directly.
"""

from typing import Any, Dict, List

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from loguru import logger

from agent.prompt.prompts import SUPERVISOR_SYSTEM_PROMPT
from agent.tools.rag import build_rag_search_tool
from services.rag_service import RAGService


def build_supervisor_agent(
    model: BaseChatModel,
    rag_service: RAGService,
    subagents: List[Dict[str, Any]],
    checkpointer: Any,
) -> Any:
    """Build the supervisor deep agent with RAG tool and subagents.

    Args:
        model (BaseChatModel): Chat model from infrastructure/llm factory.
        rag_service (RAGService): Retrieval use case for the rag_search tool.
        subagents (List[Dict[str, Any]]): SubAgent specs (e.g. data-ops)
            built by agent/subagent builders and wired in api/.
        checkpointer (Any): LangGraph checkpointer (SQLite saver) so the
            graph state persists across interrupts.

    Returns:
        Any: Compiled agent graph, invokable with {"messages": [...]}.
    """
    logger.info("Building supervisor agent [subagents={}]", [s["name"] for s in subagents])
    return create_deep_agent(
        model=model,
        tools=[build_rag_search_tool(rag_service)],
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        subagents=subagents,
        checkpointer=checkpointer,
    )
