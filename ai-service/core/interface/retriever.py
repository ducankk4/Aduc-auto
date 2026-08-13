"""Contract for knowledge-base retrieval."""

from typing import List, Protocol

from core.domain.knowledge import KnowledgeChunk


class RetrieverProtocol(Protocol):
    """Contract any knowledge retriever must satisfy."""

    async def search(self, query: str, top_k: int) -> List[KnowledgeChunk]:
        """Return the top_k chunks most similar to the query."""
        ...
