"""Port describing what ai-service needs from the RAG vector store.

Implemented by `infrastructure.rag.qdrant_retriever.QdrantRetriever`. Tools
and ingestion use cases depend on this protocol only — never on
qdrant-client or sentence-transformers directly (see code-style.md #6).
"""

from __future__ import annotations

from typing import Protocol

from ai_service.application.dto.knowledge import KnowledgeChunkDTO, RetrievedChunkDTO


class RetrieverPort(Protocol):
    async def search(self, query: str, top_k: int = 5) -> list[RetrievedChunkDTO]:
        """Return the top_k chunks most relevant to a query.

        Args:
            query: Free-text query, typically the user's question verbatim.
            top_k: Maximum number of chunks to return.

        Raises:
            RetrieverUnavailableError: the vector store is unreachable.
        """
        ...

    async def upsert_chunks(self, chunks: list[KnowledgeChunkDTO]) -> None:
        """Index new chunks into the vector store (used by the ingestion
        pipeline, not by chat-turn tools).

        Args:
            chunks: Chunks to embed and index.

        Raises:
            RetrieverUnavailableError: the vector store is unreachable.
        """
        ...
