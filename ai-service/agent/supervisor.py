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

    logger.info("Building supervisor agent [subagents={}]", [s["name"] for s in subagents])
    return create_deep_agent(
        model=model,
        tools=[build_rag_search_tool(rag_service)],
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        subagents=subagents,
        checkpointer=checkpointer,
    )
