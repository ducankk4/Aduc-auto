"""Chat model factory — the only module that constructs ChatGroq
instances. Model name and API key always come from Settings, never hardcoded
here (see CLAUDE.md: default model/provider is a product decision, not to be
changed without the user's explicit request).
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq

from ai_service.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    return ChatGroq(model=settings.model_supervisor, api_key=settings.groq_api_key)
