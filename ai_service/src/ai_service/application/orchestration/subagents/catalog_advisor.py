"""catalog_advisor subagent: browses, explains, and compares vehicles.

Wrapped as a single delegation tool for the supervisor
(`build_catalog_advisor_tool`) since LangChain 1.3.14 ships no built-in
agent-as-tool transformer (verified against the installed package — see
supervisor.py). Each delegation call runs the nested graph with a fresh,
isolated message history rather than the supervisor's full conversation, so
the subagent gets its own lean context window (roadmap 4.1).
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph.state import CompiledStateGraph

from ai_service.application.orchestration.prompts.catalog_advisor_prompt import (
    CATALOG_ADVISOR_SYSTEM_PROMPT,
)


def build_catalog_advisor_graph(
    model: BaseChatModel, tools: list[BaseTool]
) -> CompiledStateGraph:
    """Build the compiled catalog_advisor subagent graph.

    No checkpointer: every delegation call is stateless. Vehicle data is
    always fetched fresh via tools (roadmap invariant #5), so there is no
    cross-turn state worth persisting for this subagent.
    """
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=CATALOG_ADVISOR_SYSTEM_PROMPT,
        name="catalog_advisor",
    )


def build_catalog_advisor_tool(graph: CompiledStateGraph) -> BaseTool:
    """Wrap the catalog_advisor graph as a delegation tool for the supervisor."""

    @tool
    async def catalog_advisor(task: str) -> str:
        """Delegate a vehicle discovery, explanation, or comparison task to
        the catalog specialist subagent.

        Use for anything about browsing the catalog, explaining one
        vehicle's configuration/price, comparing multiple vehicles, or
        answering general/FAQ questions about vehicles or dealership
        policy. Do NOT use for leads, test-drive registration, orders, or
        admin actions — those belong to other subagents not yet available.

        Args:
            task: Self-contained description of what to find out, in the
                user's own words plus any info already known (e.g. vehicle
                slugs already mentioned earlier in the conversation). The
                subagent has no memory of the rest of the conversation, so
                include everything it needs to act without asking back.

        Returns:
            The catalog specialist's findings as text, ready to be
            summarized into a reply for the end user.
        """
        result = await graph.ainvoke({"messages": [HumanMessage(content=task)]})
        final_message = result["messages"][-1]
        content = final_message.content
        return content if isinstance(content, str) else str(content)

    return catalog_advisor
