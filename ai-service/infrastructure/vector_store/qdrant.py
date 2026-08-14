"""Knowledge-base vector store backed by Qdrant.

Maps LangChain Documents into domain entities so no other layer sees
vector-store types.
"""

from typing import List

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from loguru import logger

from core.config import settings
from core.domain.rag import Chunk, MetadataChunk, VectorSearchResult
from core.exceptions import InfrastructureError
from core.interface.repository import IDocumentRepository


def build_embeddings() -> HuggingFaceEmbeddings:
    """Build the local HuggingFace embedding model configured in Settings.

    Returns:
        HuggingFaceEmbeddings: Ready-to-use embedding function.
    """
    logger.info("Loading embedding model [model={}]", settings.EMBEDDING_MODEL)
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)


def build_vector_store(embeddings: HuggingFaceEmbeddings) -> QdrantVectorStore:
    """Connect to the existing Qdrant collection configured in Settings.

    Fails fast if the collection does not exist yet — run
    `uv run python scripts/ingest_knowledge.py` first.

    Args:
        embeddings (HuggingFaceEmbeddings): Embedding function, from build_embeddings().

    Returns:
        QdrantVectorStore: Vector store bound to the knowledge collection.
    """
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=settings.QDRANT_COLLECTION,
        url=settings.QDRANT_URL,
    )


class QdrantDocumentRepository(IDocumentRepository):
    """Similarity search over the knowledge collection in Qdrant."""

    def __init__(self, vector_store: QdrantVectorStore) -> None:
        self._vector_store = vector_store

    async def vector_search(self, query: str, top_k: int) -> List[VectorSearchResult]:
        """Return the top_k chunks most similar to the query, best score first.

        Args:
            query (str): Natural-language search query.
            top_k (int): Maximum number of chunks to return.

        Returns:
            List[VectorSearchResult]: Matching chunks with their score.

        Raises:
            InfrastructureError: If the Qdrant call fails.
        """
        try:
            hits = await self._vector_store.asimilarity_search_with_score(query, k=top_k)
        except Exception as exc:
            raise InfrastructureError(f"Không truy vấn được vector store: {exc}") from exc

        results = [_to_domain(document, score) for document, score in hits]
        logger.debug("Vector search done [query_len={}, hits={}]", len(query), len(results))
        return results


def _to_domain(document, score: float) -> VectorSearchResult:
    """Map one LangChain Document plus its score into a VectorSearchResult."""
    metadata = document.metadata
    return VectorSearchResult(
        chunk=Chunk(
            id=str(metadata.get("_id", "")),
            content=document.page_content,
            metadata=MetadataChunk(
                document_id=metadata.get("document_id", "unknown"),
                title=metadata.get("title", "unknown"),
                source_file=metadata.get("source_file", "unknown"),
                chunk_index=metadata.get("chunk_index", 0),
            ),
        ),
        similarity_score=score,
    )
