"""Qdrant-backed implementation of RetrieverPort — the only module that
imports qdrant-client. Translates client/network failures into
RetrieverUnavailableError (error-handling-logging.md #3.1).
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from ai_service.application.dto.knowledge import KnowledgeChunkDTO, RetrievedChunkDTO
from ai_service.application.ports.retriever_port import RetrieverPort
from ai_service.config import Settings
from ai_service.infrastructure.rag.embedding import SentenceTransformerEmbedder
from ai_service.infrastructure.rag.exceptions import RetrieverUnavailableError

_CONTENT_KEY = "content"
_SOURCE_KEY = "source"
_VEHICLE_SLUG_KEY = "vehicle_slug"
_SYNCED_AT_KEY = "synced_at"

_QDRANT_ERRORS = (httpx.HTTPError, UnexpectedResponse)


class QdrantRetriever(RetrieverPort):
    """Typed async client for the ai-service RAG collection in Qdrant."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        embedder: SentenceTransformerEmbedder,
        collection_name: str,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection_name = collection_name

    @classmethod
    async def build(
        cls, settings: Settings, embedder: SentenceTransformerEmbedder
    ) -> "QdrantRetriever":
        client = AsyncQdrantClient(url=settings.qdrant_url)
        retriever = cls(client, embedder, settings.qdrant_collection_name)
        await retriever._ensure_collection()
        return retriever

    async def aclose(self) -> None:
        await self._client.close()

    async def _ensure_collection(self) -> None:
        try:
            exists = await self._client.collection_exists(self._collection_name)
            if not exists:
                await self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=models.VectorParams(
                        size=self._embedder.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
        except _QDRANT_ERRORS as err:
            raise RetrieverUnavailableError("Vector store is unreachable.") from err

    async def search(self, query: str, top_k: int = 5) -> list[RetrievedChunkDTO]:
        try:
            query_vector = await self._embedder.embed_query(query)
            result = await self._client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                limit=top_k,
            )
        except _QDRANT_ERRORS as err:
            raise RetrieverUnavailableError("Vector store is unreachable.") from err

        return [self._to_retrieved_chunk(point.payload, point.score) for point in result.points]

    async def upsert_chunks(self, chunks: list[KnowledgeChunkDTO]) -> None:
        if not chunks:
            return

        try:
            vectors = await self._embedder.embed_documents([chunk.content for chunk in chunks])
            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        _CONTENT_KEY: chunk.content,
                        _SOURCE_KEY: chunk.source,
                        _VEHICLE_SLUG_KEY: chunk.vehicle_slug,
                        _SYNCED_AT_KEY: chunk.synced_at.isoformat(),
                    },
                )
                for chunk, vector in zip(chunks, vectors)
            ]
            await self._client.upsert(collection_name=self._collection_name, points=points)
        except _QDRANT_ERRORS as err:
            raise RetrieverUnavailableError("Vector store is unreachable.") from err

    @staticmethod
    def _to_retrieved_chunk(payload: dict[str, Any] | None, score: float) -> RetrievedChunkDTO:
        payload = payload or {}
        return RetrievedChunkDTO(
            content=payload.get(_CONTENT_KEY, ""),
            source=payload.get(_SOURCE_KEY, ""),
            vehicle_slug=payload.get(_VEHICLE_SLUG_KEY),
            score=score,
        )
