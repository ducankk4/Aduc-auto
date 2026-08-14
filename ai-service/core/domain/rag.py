from dataclasses import dataclass


@dataclass(frozen=True)
class MetadataChunk:
    """Identity of a chunk within its source document, set once at ingest time."""

    document_id: str
    title: str
    source_file: str
    chunk_index: int


@dataclass(frozen=True)
class Chunk:
    """One fragment of the knowledge base."""

    id: str
    content: str
    metadata: MetadataChunk


@dataclass(frozen=True)
class VectorSearchResult:
    """A chunk paired with how well it matched one specific query."""

    chunk: Chunk
    similarity_score: float
