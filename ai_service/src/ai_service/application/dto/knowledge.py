"""DTOs describing RAG knowledge chunks as they cross application layer
boundaries. Chunk content must never contain price/deposit/stock numbers —
that is a data-entry and ingestion-time concern (roadmap invariant #5), not
something these DTOs enforce.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class KnowledgeChunkDTO:
    """One chunk to be indexed into the vector store."""

    content: str
    source: str
    vehicle_slug: str | None
    synced_at: datetime


@dataclass(frozen=True)
class RetrievedChunkDTO:
    """One chunk returned from a similarity search, with its relevance score."""

    content: str
    source: str
    vehicle_slug: str | None
    score: float
