"""Phase 0 exit-criteria smoke test: graph + SQLite checkpoint + interrupt/resume.

What it proves:
1. A graph compiles with the SQLite checkpointer.
2. `interrupt()` pauses the run and the state survives in checkpoints.db.
3. `Command(resume=...)` continues the SAME thread from where it stopped.

Run:  uv run python scripts/smoke_checkpoint.py
"""

import asyncio
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from loguru import logger

from agent.state import SupervisorState
from core.checkpointer import open_checkpointer
from core.logger import setup_logger

_THREAD_ID = "smoke-checkpoint-1"


async def ask_approval_node(state: SupervisorState) -> Dict[str, Any]:
    """Pause the graph and wait for a human decision before answering."""
    decision = interrupt("Bạn có duyệt cho graph chạy tiếp không?")
    return {"messages": [AIMessage(content=f"Đã resume với quyết định: {decision}")]}


async def main() -> None:
    """Run the interrupt/resume round-trip against the real SQLite checkpointer."""
    setup_logger()

    async with open_checkpointer() as checkpointer:
        builder = StateGraph(SupervisorState)
        builder.add_node("ask_approval", ask_approval_node)
        builder.add_edge(START, "ask_approval")
        builder.add_edge("ask_approval", END)
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": _THREAD_ID}}

        # Lượt 1: graph phải dừng ở interrupt, KHÔNG chạy tới cuối.
        first = await graph.ainvoke(
            {"messages": [HumanMessage(content="xin chào")]}, config
        )
        interrupts = first.get("__interrupt__")
        assert interrupts, "FAIL: graph không dừng ở interrupt — kiểm tra checkpointer"
        logger.info("Interrupt OK [payload={}]", interrupts[0].value)

        # Lượt 2: resume trên CÙNG thread_id — phải chạy nốt tới END.
        second = await graph.ainvoke(Command(resume="approved"), config)
        last_message = second["messages"][-1]
        assert "approved" in last_message.content, (
            "FAIL: resume không mang quyết định vào state — kiểm tra thread_id"
        )
        logger.info("Resume OK [last_message={}]", last_message.content)

    logger.info("Smoke test PASSED — Phase 0 checkpoint/resume hoạt động")


if __name__ == "__main__":
    asyncio.run(main())
