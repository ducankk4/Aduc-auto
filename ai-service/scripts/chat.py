"""Console chat with the supervisor agent — Phase 1 exit-criteria check.

What it proves:
1. Supervisor answers policy/FAQ questions by calling rag_search (RAG works).
2. Supervisor delegates vehicle-data questions to the data-ops stub
   subagent via the built-in task tool (delegation works).

Prerequisites: Qdrant running + knowledge ingested (scripts/ingest_knowledge.py).
Run:  uv run python scripts/chat.py
Exit: gõ 'q' hoặc Ctrl+C.
"""

import asyncio
import uuid

from langchain_core.messages import HumanMessage
from loguru import logger

from api.dependencies import build_supervisor
from core.checkpointer import open_checkpointer
from core.logger import setup_logger


async def main() -> None:
    """Run an interactive chat loop against the wired supervisor."""
    setup_logger()

    async with open_checkpointer() as checkpointer:
        agent = build_supervisor(checkpointer)
        thread_id = f"chat-{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        logger.info("Chat session started [thread_id={}]", thread_id)
        print("Gõ câu hỏi (q để thoát). Ví dụ:")
        print("  - Chính sách hoàn tiền đặt cọc thế nào?   -> phải thấy rag_search chạy")
        print("  - Bên em đang có những xe nào?            -> phải thấy giao cho data-ops stub")

        while True:
            try:
                user_input = input("\nAnh: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input or user_input.lower() == "q":
                break

            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_input)]}, config
            )
            for message in result["messages"]:
                for tool_call in getattr(message, "tool_calls", []) or []:
                    logger.info(
                        "Tool call [name={}, args={}]", tool_call["name"], tool_call["args"]
                    )
            print(f"\nAI: {result['messages'][-1].content}")

    logger.info("Chat session ended [thread_id={}]", thread_id)


if __name__ == "__main__":
    asyncio.run(main())
