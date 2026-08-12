"""Read-only RAG search tool exposed to the catalog_advisor subagent."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from loguru import logger

from ai_service.application.dto.knowledge import RetrievedChunkDTO
from ai_service.application.ports.retriever_port import RetrieverPort
from ai_service.infrastructure.rag.exceptions import RetrieverUnavailableError


def build_rag_tools(retriever_port: RetrieverPort) -> list[BaseTool]:
    """Build the RAG toolset bound to a concrete RetrieverPort implementation."""

    @tool
    async def rag_search(query: str, top_k: int = 5) -> str:
        """Search static knowledge content: vehicle descriptions, FAQ, and
        dealership policy (deposit/cancellation/refund, test-drive guidance).

        Use for general or background questions that are NOT about a live
        price, deposit amount, stock, or order status — those always come
        from `get_vehicle_detail` or order tools, never from this search.
        Good for e.g. "what is your cancellation policy?", "tell me about
        the VF8's design", "how does the test drive process work?".

        Args:
            query: The user's question, in their own words.
            top_k: Maximum number of matching chunks to return (1-10).

        Returns:
            Formatted text with the matching chunks and their source, ready
            for the model to read. Returns a plain "no results" message
            (not an error) if nothing relevant was found, and an error
            message if the vector store is unreachable.
        """
        try:
            chunks = await retriever_port.search(query, top_k=top_k)
        except RetrieverUnavailableError as err:
            logger.bind(operation="rag_search").warning("Retriever unavailable: {}", err)
            return "Error: the knowledge base is temporarily unavailable, please try again later."

        if not chunks:
            return "No relevant knowledge base content found for this query."

        return _format_chunks(chunks)

    return [rag_search]


def _format_chunks(chunks: list[RetrievedChunkDTO]) -> str:
    lines = ["Knowledge base results:"]
    for chunk in chunks:
        lines.append(f"- (source={chunk.source}, score={chunk.score:.2f}) {chunk.content}")
    return "\n".join(lines)
