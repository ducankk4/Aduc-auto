"""Interactive console chat against the supervisor agent, without HTTP.

Exercises the same graph the API serves, including the HITL approval
flow: when a sensitive tool interrupts, the console asks for
approve / edit / reject and resumes on the same thread.

Run:  uv run python scripts/chat.py
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from loguru import logger

from agent.checkpointer import open_checkpointer
from agent.hitl import build_decision, build_resume_command, pending_approvals
from api.dependencies import build_supervisor
from core.logger import setup_logger
from core.masking import mask_sensitive_args


def _ask_decision(approval: Dict[str, Any]) -> Dict[str, Any]:
    """Prompt the console user for one approval decision."""
    print("\n--- YÊU CẦU PHÊ DUYỆT ---")
    print(f"Tool: {approval['tool']}")
    print(f"Tham số: {json.dumps(approval['args'], ensure_ascii=False, indent=2)}")
    while True:
        choice = input("Phê duyệt? [y=đồng ý / e=sửa tham số / n=từ chối]: ").strip().lower()
        if choice == "y":
            return build_decision("approve")
        if choice == "e":
            raw = input("Nhập tham số mới (JSON): ").strip()
            try:
                new_args = json.loads(raw)
            except json.JSONDecodeError:
                print("JSON không hợp lệ, thử lại.")
                continue
            return build_decision("edit", tool=approval["tool"], args=new_args)
        if choice == "n":
            message = input("Lý do từ chối (Enter để bỏ qua): ").strip()
            return build_decision("reject", message=message or None)
        print("Chỉ nhận y / e / n.")


async def _resolve_interrupts(
    supervisor: Any, result: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Loop over pending interrupts, collecting decisions and resuming."""
    thread_id = config["configurable"]["thread_id"]
    while True:
        approvals = pending_approvals(result)
        if not approvals:
            return result
        decisions: List[Dict[str, Any]] = []
        for approval in approvals:
            logger.info(
                "HITL interrupt [thread_id={}, tool={}, args={}]",
                thread_id,
                approval["tool"],
                mask_sensitive_args(approval["args"]),
            )
            decision = _ask_decision(approval)
            logger.info(
                "HITL decision [thread_id={}, tool={}, decision={}]",
                thread_id,
                approval["tool"],
                decision["type"],
            )
            decisions.append(decision)
        result = await supervisor.ainvoke(build_resume_command(decisions), config)


async def main() -> None:
    """Run the console chat loop until the user types exit."""
    setup_logger()
    async with open_checkpointer() as checkpointer:
        supervisor = build_supervisor(checkpointer)
        # In-memory stand-in for conversation history: each turn is a fresh
        # thread (mirroring the API), so context must be carried explicitly.
        messages: List[Any] = []
        print("Chat console — gõ 'exit' để thoát.")
        while True:
            question = input("\nBạn: ").strip()
            if not question or question.lower() in {"exit", "quit"}:
                break
            session_id = f"cli-{uuid.uuid4().hex[:8]}"
            config = {"configurable": {"thread_id": session_id}}
            result = await supervisor.ainvoke(
                {"messages": [*messages, HumanMessage(question)]}, config
            )
            result = await _resolve_interrupts(supervisor, result, config)
            reply = result["messages"][-1].content
            print(f"\nTrợ lý: {reply}")
            messages = result["messages"]


if __name__ == "__main__":
    asyncio.run(main())