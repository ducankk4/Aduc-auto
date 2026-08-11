"""Supervisor agent graph construction.

Phase 0: a single agent with one read tool, no subagent delegation. LangChain
1.3.14 ships no ready-made "agent as tool" transformer (verified against the
installed package) — subagent wrapping in later phases will need a thin
`@tool` wrapper around a nested `create_agent(..., name=...)` graph.
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
