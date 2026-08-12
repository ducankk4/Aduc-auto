"""Unit tests for the `rag_search` tool's error handling — per
error-handling-logging.md #5, a tool must return error text instead of
letting a port exception propagate and break the graph.
"""

from __future__ import annotations

from ai_service.application.dto.knowledge import RetrievedChunkDTO
from ai_service.application.tools.rag_tools import build_rag_tools
from ai_service.infrastructure.rag.exceptions import RetrieverUnavailableError


class _UnavailableRetrieverPort:
    async def search(self, query: str, top_k: int = 5):
        raise RetrieverUnavailableError("vector store down")

    async def upsert_chunks(self, chunks):
        raise RetrieverUnavailableError("vector store down")


class _EmptyRetrieverPort:
    async def search(self, query: str, top_k: int = 5):
        return []

    async def upsert_chunks(self, chunks):
        return None


class _WorkingRetrieverPort:
    async def search(self, query: str, top_k: int = 5):
        return [
            RetrievedChunkDTO(
                content="Deposits are refundable within 48 hours of payment.",
                source="knowledge:policy",
                vehicle_slug=None,
                score=0.87,
            )
        ]

    async def upsert_chunks(self, chunks):
        return None


async def test_rag_search_returns_error_text_when_retriever_unavailable():
    tools = build_rag_tools(_UnavailableRetrieverPort())
    rag_search = tools[0]

    result = await rag_search.ainvoke({"query": "cancellation policy"})

    assert result.startswith("Error:")


async def test_rag_search_reports_no_results_without_error():
    tools = build_rag_tools(_EmptyRetrieverPort())
    rag_search = tools[0]

    result = await rag_search.ainvoke({"query": "cancellation policy"})

    assert not result.startswith("Error:")
    assert "No relevant" in result


async def test_rag_search_formats_chunks_from_retriever():
    tools = build_rag_tools(_WorkingRetrieverPort())
    rag_search = tools[0]

    result = await rag_search.ainvoke({"query": "refund policy"})

    assert "refundable within 48 hours" in result
    assert "knowledge:policy" in result
