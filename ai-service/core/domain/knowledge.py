"""Knowledge-base domain entities for RAG."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeChunk:
    """One retrieved fragment of the knowledge base.

    Attributes:
        content: The chunk text.
        source: Originating document (file name), used for citation.
        score: Similarity score returned by the vector store (higher = closer).
    """

    content: str
    source: str
    score: float
