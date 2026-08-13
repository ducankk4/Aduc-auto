"""RAG use case: retrieve knowledge chunks for a question.

Answer synthesis is intentionally NOT here — the supervisor LLM composes
the final answer from the chunks this service returns, so retrieval logic
stays testable without any LLM involved.
"""

from typing import List

from loguru import logger

from core.config import settings
from core.domain.knowledge import KnowledgeChunk
from core.interface.retriever import RetrieverProtocol


class RAGService:
    """Use cases for knowledge-base retrieval."""

    def __init__(self, retriever: RetrieverProtocol) -> None:
        self._retriever = retriever

    async def search_knowledge(self, query: str) -> List[KnowledgeChunk]:
        """Retrieve the knowledge chunks most relevant to a user question.

        Args:
            query (str): Natural-language question from the user.

        Returns:
            List[KnowledgeChunk]: Up to RAG_TOP_K chunks, best match first.
        """
        chunks = await self._retriever.search(query, top_k=settings.RAG_TOP_K)
        logger.info(
            "Knowledge retrieved [query_len={}, hits={}, sources={}]",
            len(query),
            len(chunks),
            sorted({chunk.source for chunk in chunks}),
        )
        return chunks
