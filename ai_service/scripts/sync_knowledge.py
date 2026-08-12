"""Manual trigger for the RAG knowledge sync (roadmap section 7: "job định
kỳ + trigger thủ công" — only the manual path exists in Phase 1).

Run with: uv run python scripts/sync_knowledge.py

Ingests vehicle descriptions (via BackendPort) and markdown files under
KNOWLEDGE_DIR into the vector store. Wires only the two ports
SyncKnowledgeUseCase needs directly, rather than the full app container —
this script never starts the FastAPI app or builds the chat/agent graph.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from ai_service.application.use_cases.sync_knowledge_use_case import SyncKnowledgeUseCase
from ai_service.config import get_settings
from ai_service.infrastructure.backend.client import BackendHttpClient
from ai_service.infrastructure.rag.embedding import SentenceTransformerEmbedder
from ai_service.infrastructure.rag.qdrant_retriever import QdrantRetriever


async def main() -> None:
    settings = get_settings()

    backend_client = BackendHttpClient.build(settings)
    embedder = SentenceTransformerEmbedder.build(settings)
    retriever = await QdrantRetriever.build(settings, embedder)

    try:
        use_case = SyncKnowledgeUseCase(
            backend_port=backend_client,
            retriever_port=retriever,
            knowledge_dir=Path(settings.knowledge_dir),
        )
        count = await use_case.sync_all()
        logger.info("Knowledge sync finished: {} chunks indexed", count)
    finally:
        await backend_client.aclose()
        await retriever.aclose()


if __name__ == "__main__":
    asyncio.run(main())
