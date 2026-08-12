"""Embedding adapter — the only module that imports sentence-transformers.

Self-hosted, in-process embedding: no separate service, no API key. The
model is loaded once at startup (see `build`) and reused for every call.
Inference is CPU-bound and blocking, so calls are offloaded to a thread via
`asyncio.to_thread` to keep the event loop free (code-style.md #1).
"""

from __future__ import annotations

import asyncio

from sentence_transformers import SentenceTransformer

from ai_service.config import Settings


class SentenceTransformerEmbedder:
    """Wraps a locally loaded sentence-transformers model."""

    def __init__(self, model: SentenceTransformer) -> None:
        self._model = model

    @classmethod
    def build(cls, settings: Settings) -> "SentenceTransformerEmbedder":
        model = SentenceTransformer(settings.embedding_model_name)
        return cls(model)

    @property
    def vector_size(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        vectors = await asyncio.to_thread(self._model.encode, [text])
        return vectors[0].tolist()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk contents for indexing."""
        vectors = await asyncio.to_thread(self._model.encode, texts)
        return [vector.tolist() for vector in vectors]
