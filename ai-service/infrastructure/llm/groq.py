from langchain_groq import ChatGroq
from loguru import logger

from core.config import settings


def build_chat_model() -> ChatGroq:
    """Build the Groq chat model configured in Settings.

    Returns:
        ChatGroq: Ready-to-use LangChain chat model.
    """
    logger.debug("Building chat model [model={}]", settings.LLM_MODEL)
    return ChatGroq(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.GROQ_API_KEY,
    )
