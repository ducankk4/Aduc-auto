from typing import List

from loguru import logger

from core.config import settings
from core.domain.rag import VectorSearchResult
from core.interface.repository import IDocumentRepository


class RAGService:
    """Use cases for knowledge-base retrieval."""

    def __init__(self, document_repository: IDocumentRepository) -> None:
        self._document_repository = document_repository

    async def search_knowledge(self, query: str) -> List[VectorSearchResult]:
        """Retrieve the knowledge chunks most relevant to a user question.

        Args:
            query (str): Natural-language question from the user.

        Returns:
            List[VectorSearchResult]: Up to RAG_TOP_K chunks, best match first.
        """
        results = await self._document_repository.vector_search(query, top_k=settings.RAG_TOP_K)
        logger.info(
            "Knowledge retrieved [query_len={}, hits={}, sources={}]",
            len(query),
            len(results),
            sorted({result.chunk.metadata.source_file for result in results}),
        )
        return results
