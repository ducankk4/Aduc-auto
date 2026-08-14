from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from uuid import UUID

from core.domain.booking import TestDriveBooking
from core.domain.car import Car
from core.domain.message import Conversation
from core.domain.rag import VectorSearchResult


class ICarRepository(ABC):
    """Contract any vehicle data source must satisfy."""

    @abstractmethod
    async def find_many(self, page: int = 1, limit: int = 20) -> Tuple[List[Car], int]:
        """Return a page of active vehicles and the total vehicle count."""
        ...

    @abstractmethod
    async def find_by_slug(self, slug: str) -> Optional[Car]:
        """Return the vehicle matching the given slug, or None if absent."""
        ...


class IBookingRepository(ABC):
    """Contract any test-drive booking sink must satisfy."""

    @abstractmethod
    async def create(
        self,
        vehicle_id: UUID,
        customer_name: str,
        phone: str,
        email: str,
        showroom_pref: Optional[str] = None,
    ) -> TestDriveBooking:
        """Register a test-drive booking and return the stored record."""
        ...


class IDocumentRepository(ABC):
    """Contract any knowledge-base vector store must satisfy."""

    @abstractmethod
    async def vector_search(self, query: str, top_k: int) -> List[VectorSearchResult]:
        """Return the top_k chunks most similar to the query, best score first."""
        ...


class IMessageRepository(ABC):
    """Contract any conversation history store must satisfy."""

    @abstractmethod
    async def find_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Return the conversation with the given id, or None if absent."""
        ...

    @abstractmethod
    async def create_conversation(self, conversation: Conversation) -> None:
        """Persist a brand-new conversation."""
        ...

    @abstractmethod
    async def update_conversation(self, conversation: Conversation) -> None:
        """Overwrite an existing conversation (new turns, updated timestamp)."""
        ...
