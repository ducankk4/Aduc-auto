"""Unit tests for SyncKnowledgeUseCase: price-stripping heuristic, markdown
chunking, and the overall sync flow against fake ports (no real backend or
vector store — mock at the port boundary per code-style.md #7).
"""

from __future__ import annotations

from pathlib import Path

from ai_service.application.dto.vehicle import VehicleDetailDTO, VehicleSummaryDTO
from ai_service.application.use_cases.sync_knowledge_use_case import (
    SyncKnowledgeUseCase,
    _split_into_chunks,
    _strip_price_numbers,
)
from ai_service.infrastructure.backend.exceptions import BackendNotFoundError


class _FakeBackendPort:
    def __init__(self, vehicles, details):
        self._vehicles = vehicles
        self._details = details

    async def list_vehicles(self, page: int = 1, limit: int = 20):
        return self._vehicles

    async def get_vehicle_detail(self, slug: str):
        if slug not in self._details:
            raise BackendNotFoundError("Vehicle not found")
        return self._details[slug]


class _FakeRetrieverPort:
    def __init__(self):
        self.upserted = []

    async def search(self, query: str, top_k: int = 5):
        return []

    async def upsert_chunks(self, chunks):
        self.upserted.extend(chunks)


def _vehicle(slug: str, description: str | None) -> tuple[VehicleSummaryDTO, VehicleDetailDTO]:
    summary = VehicleSummaryDTO(
        id="00000000-0000-0000-0000-000000000001",
        name="VF8",
        slug=slug,
        category="SUV",
        base_price=1_000_000_000,
        is_active=True,
    )
    detail = VehicleDetailDTO(
        id="00000000-0000-0000-0000-000000000001",
        name="VF8",
        slug=slug,
        category="SUV",
        description=description,
        base_price=1_000_000_000,
        is_active=True,
        variants=[],
        colors=[],
    )
    return summary, detail


def test_strip_price_numbers_removes_grouped_thousands_amounts():
    text = "Giá niêm yết 1.200.000.000 VND, đã bao gồm thuế."

    result = _strip_price_numbers(text)

    assert "1.200.000.000" not in result
    assert "[price omitted]" in result


def test_strip_price_numbers_keeps_small_spec_numbers():
    text = "SUV 7 chỗ, động cơ 2.0L, quãng đường di chuyển 500km."

    result = _strip_price_numbers(text)

    assert result == text


def test_split_into_chunks_groups_paragraphs_under_max_chars():
    text = "Đoạn 1.\n\nĐoạn 2.\n\nĐoạn 3."

    chunks = _split_into_chunks(text, max_chars=15)

    assert chunks == ["Đoạn 1.", "Đoạn 2.", "Đoạn 3."]


def test_split_into_chunks_merges_short_paragraphs():
    text = "A.\n\nB.\n\nC."

    chunks = _split_into_chunks(text, max_chars=100)

    assert chunks == ["A.\n\nB.\n\nC."]


async def test_sync_all_indexes_vehicle_description_and_strips_price(tmp_path: Path):
    summary, detail = _vehicle("vf8", "Xe điện SUV, giá 1.200.000.000 VND.")
    backend_port = _FakeBackendPort(vehicles=[summary], details={"vf8": detail})
    retriever_port = _FakeRetrieverPort()

    use_case = SyncKnowledgeUseCase(
        backend_port=backend_port, retriever_port=retriever_port, knowledge_dir=tmp_path
    )
    count = await use_case.sync_all()

    assert count == 1
    assert "1.200.000.000" not in retriever_port.upserted[0].content
    assert retriever_port.upserted[0].vehicle_slug == "vf8"


async def test_sync_all_skips_vehicles_without_description(tmp_path: Path):
    summary, detail = _vehicle("vf8", None)
    backend_port = _FakeBackendPort(vehicles=[summary], details={"vf8": detail})
    retriever_port = _FakeRetrieverPort()

    use_case = SyncKnowledgeUseCase(
        backend_port=backend_port, retriever_port=retriever_port, knowledge_dir=tmp_path
    )
    count = await use_case.sync_all()

    assert count == 0


async def test_sync_all_ingests_markdown_files(tmp_path: Path):
    content = "Chính sách hoàn tiền trong 48 giờ."
    (tmp_path / "policy.md").write_text(content, encoding="utf-8")
    backend_port = _FakeBackendPort(vehicles=[], details={})
    retriever_port = _FakeRetrieverPort()

    use_case = SyncKnowledgeUseCase(
        backend_port=backend_port, retriever_port=retriever_port, knowledge_dir=tmp_path
    )
    count = await use_case.sync_all()

    assert count == 1
    assert retriever_port.upserted[0].source == "knowledge:policy"


async def test_sync_all_handles_missing_knowledge_dir_gracefully(tmp_path: Path):
    backend_port = _FakeBackendPort(vehicles=[], details={})
    retriever_port = _FakeRetrieverPort()

    use_case = SyncKnowledgeUseCase(
        backend_port=backend_port,
        retriever_port=retriever_port,
        knowledge_dir=tmp_path / "does-not-exist",
    )
    count = await use_case.sync_all()

    assert count == 0
