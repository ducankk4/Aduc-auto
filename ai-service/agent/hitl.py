"""HITL bridge: middleware interrupt payloads mapped to plain data and back.

The only place outside HumanInTheLoopMiddleware that knows its wire
shapes (HITLRequest / HITLResponse), so api/ and scripts/ deal in plain
dicts and never touch LangGraph types directly.
"""

from typing import Any, Dict, List, Optional

from langgraph.types import Command

_DEFAULT_DECISIONS = ["approve", "edit", "reject"]


def pending_approvals(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract pending approval requests from an invoke result.

    Args:
        result (Dict[str, Any]): Return value of graph.ainvoke().

    Returns:
        List[Dict[str, Any]]: One {tool, args, allowed_decisions} per
            sensitive tool call awaiting review; empty if not interrupted.
    """
    if not result.get("__interrupt__"):
        return []
    request = result["__interrupt__"][0].value
    allowed = {
        config["action_name"]: list(config["allowed_decisions"])
        for config in request.get("review_configs", [])
    }
    return [
        {
            "tool": action["name"],
            "args": dict(action["args"]),
            "allowed_decisions": allowed.get(action["name"], _DEFAULT_DECISIONS),
        }
        for action in request["action_requests"]
    ]


def build_decision(
    decision_type: str,
    tool: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Map one human decision onto the middleware decision format.

    Args:
        decision_type (str): "approve", "edit", or "reject".
        tool (Optional[str]): Tool name, required for "edit".
        args (Optional[Dict[str, Any]]): New arguments, required for "edit".
        message (Optional[str]): Optional reason shown to the model on "reject".

    Returns:
        Dict[str, Any]: Decision in the shape HumanInTheLoopMiddleware expects.
    """
    if decision_type == "approve":
        return {"type": "approve"}
    if decision_type == "edit":
        return {"type": "edit", "edited_action": {"name": tool, "args": args or {}}}
    decision: Dict[str, Any] = {"type": "reject"}
    if message:
        decision["message"] = message
    return decision


def build_resume_command(decisions: List[Dict[str, Any]]) -> Command:
    """Wrap mapped decisions in the Command that resumes the halted turn."""
    return Command(resume={"decisions": decisions})
