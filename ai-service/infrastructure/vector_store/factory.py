"""Factories for the embedding model and the Qdrant vector store.

Loading the embedding model is slow (first call downloads it from
HuggingFace); build these once at startup and reuse, never per request.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from loguru import logger

from core.config import settings


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
        embeddings (HuggingFaceEmbeddings): Embedding function, from
            build_embeddings().

    Returns:
        QdrantVectorStore: Vector store bound to the knowledge collection.
    """
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=settings.QDRANT_COLLECTION,
        url=settings.QDRANT_URL,
    )
