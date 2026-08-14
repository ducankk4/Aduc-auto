from typing import Annotated, List, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupervisorState(TypedDict):
    """Shared state flowing through the supervisor graph and its subagents."""

    messages: Annotated[List[AnyMessage], add_messages]
