"""Supervisor agent graph construction.

Phase 1: the supervisor's `tools` are delegation tools only (e.g. the
`catalog_advisor` wrapper in `orchestration/subagents/`) — it holds no
business tool directly (roadmap 4.1). This function itself is agnostic to
that distinction; it just compiles whatever tool list it is given.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from ai_service.application.orchestration.context import AgentContext
from ai_service.application.orchestration.prompts.supervisor_prompt import (
    SUPERVISOR_SYSTEM_PROMPT,
)


def build_supervisor(
    model: BaseChatModel,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Build the compiled supervisor graph, checkpointed per conversation thread."""

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
        name="supervisor",
    )
