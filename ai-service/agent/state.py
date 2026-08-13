"""Shared state schemas for every graph in ai-service.

State only carries data that must survive a checkpoint. Never put
non-serializable objects (clients, sessions, connections) in state —
pass those through constructor injection or graph config instead.
"""

from typing import Annotated, List, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupervisorState(TypedDict):
    """Shared state flowing through the supervisor graph and its subagents."""

    messages: Annotated[List[AnyMessage], add_messages]
