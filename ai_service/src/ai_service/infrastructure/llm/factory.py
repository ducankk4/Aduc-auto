"""Chat model factory — the only module that constructs ChatAnthropic
instances. Model name and API key always come from Settings, never hardcoded
here (see CLAUDE.md: default model is a product decision, not to be changed
without the user's explicit request).
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from ai_service.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    return ChatAnthropic(model=settings.model_supervisor, api_key=settings.anthropic_api_key)
