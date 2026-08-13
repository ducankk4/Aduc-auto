"""Knowledge retriever backed by Qdrant.

Implements RetrieverProtocol (structurally). Maps LangChain Documents
into KnowledgeChunk entities so no other layer sees vector-store types.
"""

from typing import List

from langchain_qdrant import QdrantVectorStore
from loguru import logger

from core.domain.knowledge import KnowledgeChunk
from core.exceptions import InfrastructureError


class QdrantRetriever:
    """Similarity search over the knowledge collection in Qdrant."""

    def __init__(self, vector_store: QdrantVectorStore) -> None:
        self._vector_store = vector_store

    async def search(self, query: str, top_k: int) -> List[KnowledgeChunk]:
        """Return the top_k chunks most similar to the query.

        Args:
            query (str): Natural-language search query.
            top_k (int): Maximum number of chunks to return.

        Returns:
            List[KnowledgeChunk]: Matching chunks, best score first.

        Raises:
            InfrastructureError: If the Qdrant call fails.
        """
        try:
            results = await self._vector_store.asimilarity_search_with_score(query, k=top_k)
        except Exception as exc:
            raise InfrastructureError(f"Không truy vấn được vector store: {exc}") from exc

        chunks = [
            KnowledgeChunk(
                content=document.page_content,
                source=document.metadata.get("source", "unknown"),
                score=score,
            )
            for document, score in results
        ]
        logger.debug("Vector search done [query_len={}, hits={}]", len(query), len(chunks))
        return chunks
