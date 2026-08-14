"""Replay stored conversation history as LangChain messages.

Each turn runs on its own LangGraph thread, so the checkpointer carries no
memory between turns — earlier sessions are fed back in explicitly here.
This is the only place that maps history entities onto LangChain types.
"""

from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from core.domain.message import Session


def build_agent_messages(history: List[Session], question: str) -> List[BaseMessage]:
    """Build the message list for one agent call: past turns then the new question.

    Args:
        history (List[Session]): Past exchanges, oldest first.
        question (str): What the user is asking now.

    Returns:
        List[BaseMessage]: Alternating human/AI messages, new question last.
    """
    messages: List[BaseMessage] = []
    for session in history:
        messages.append(HumanMessage(content=session.question.content))
        messages.append(AIMessage(content=session.answer.content))
    messages.append(HumanMessage(content=question))
    return messages
