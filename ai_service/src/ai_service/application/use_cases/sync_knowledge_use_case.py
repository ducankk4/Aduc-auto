"""Use case: sync RAG knowledge chunks from backend vehicle descriptions and
local markdown policy/FAQ files into the vector store (roadmap section 7).

Triggered manually via `scripts/sync_knowledge.py` for now — no scheduled
job or HTTP endpoint yet (roadmap 7 lists both "job định kỳ" and "trigger
thủ công" as the target state; only the manual path exists in Phase 1).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from ai_service.application.dto.knowledge import KnowledgeChunkDTO
from ai_service.application.ports.backend_port import BackendPort
from ai_service.application.ports.retriever_port import RetrieverPort
from ai_service.infrastructure.backend.exceptions import BackendError

_CHUNK_MAX_CHARS = 800

# Heuristic defense-in-depth for roadmap invariant #5 ("RAG never carries
# price/deposit numbers"): strips amounts written with currency words/symbols
# and grouped-thousands numbers (e.g. "1.200.000.000", typical VND price
# formatting). Deliberately does not touch small numbers like "7 chỗ" or
# "2.0L" — those are legitimate spec content, not prices. The primary control
# is still that descriptions should not contain prices in the first place;
# this only guards against admin mistakes slipping into the corpus.
_PRICE_PATTERN = re.compile(
    r"\d[\d.,]*\s*(?:vnđ|vnd|đồng|₫)|\b\d{1,3}(?:[.,]\d{3}){2,}\b",
    re.IGNORECASE,
)


class SyncKnowledgeUseCase:
    """Depends on BackendPort (read vehicle descriptions) and RetrieverPort
    (index chunks) — the two ports this use case shares across its one
    public method (code-style.md #5).
    """

    def __init__(
        self,
        backend_port: BackendPort,
        retriever_port: RetrieverPort,
        knowledge_dir: Path,
    ) -> None:
        self._backend_port = backend_port
        self._retriever_port = retriever_port
        self._knowledge_dir = knowledge_dir

    async def sync_all(self) -> int:
        """Ingest vehicle descriptions and markdown knowledge files.

        Returns:
            The number of chunks indexed.
        """
        chunks = await self._collect_vehicle_chunks()
        chunks.extend(self._collect_markdown_chunks())

        await self._retriever_port.upsert_chunks(chunks)
        logger.bind(operation="sync_knowledge", chunk_count=len(chunks)).info(
            "Knowledge sync indexed {} chunks", len(chunks)
        )
        return len(chunks)

    async def _collect_vehicle_chunks(self) -> list[KnowledgeChunkDTO]:
        synced_at = datetime.now(timezone.utc)
        chunks: list[KnowledgeChunkDTO] = []

        try:
            vehicles = await self._backend_port.list_vehicles(page=1, limit=100)
        except BackendError as err:
            logger.bind(operation="sync_knowledge").warning(
                "Could not list vehicles for knowledge sync: {}", err
            )
            return chunks

        for summary in vehicles:
            try:
                detail = await self._backend_port.get_vehicle_detail(summary.slug)
            except BackendError as err:
                logger.bind(slug=summary.slug, operation="sync_knowledge").warning(
                    "Could not fetch vehicle detail for knowledge sync: {}", err
                )
                continue

            if not detail.description:
                continue

            chunks.append(
                KnowledgeChunkDTO(
                    content=_strip_price_numbers(detail.description),
                    source=f"vehicle:{detail.slug}",
                    vehicle_slug=detail.slug,
                    synced_at=synced_at,
                )
            )

        return chunks

    def _collect_markdown_chunks(self) -> list[KnowledgeChunkDTO]:
        if not self._knowledge_dir.is_dir():
            logger.bind(operation="sync_knowledge", path=str(self._knowledge_dir)).warning(
                "Knowledge directory does not exist, skipping markdown ingest"
            )
            return []

        synced_at = datetime.now(timezone.utc)
        chunks: list[KnowledgeChunkDTO] = []

        for path in sorted(self._knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for piece in _split_into_chunks(text):
                chunks.append(
                    KnowledgeChunkDTO(
                        content=piece,
                        source=f"knowledge:{path.stem}",
                        vehicle_slug=None,
                        synced_at=synced_at,
                    )
                )

        return chunks


def _strip_price_numbers(text: str) -> str:
    return _PRICE_PATTERN.sub("[price omitted]", text)


def _split_into_chunks(text: str, max_chars: int = _CHUNK_MAX_CHARS) -> list[str]:
    """Group markdown paragraphs into chunks up to `max_chars`, splitting on
    blank lines rather than a fixed character window so a chunk never cuts
    a sentence in half.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph

    if current:
        chunks.append(current)

    return chunks
