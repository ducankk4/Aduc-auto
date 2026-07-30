"""Unit Tests for Catalog Service (List Vehicles, Get Vehicle By Slug, Variant, Color)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest

from app.core.exceptions import NotFoundError
from app.modules.catalog.service import CatalogService


@pytest.mark.asyncio
async def test_get_by_slug_not_found_raises_not_found_error():
    """Verify get_by_slug raises NotFoundError when slug does not exist."""
    session_mock = AsyncMock()
    with patch("app.modules.catalog.repository.CatalogRepository.find_by_slug", return_value=None):
        with pytest.raises(NotFoundError) as exc_info:
            await CatalogService.get_by_slug(session_mock, "non-existent-slug")

        assert "non-existent-slug" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_variant_not_found_raises_not_found_error():
    """Verify get_variant raises NotFoundError when variant_id does not exist."""
    session_mock = AsyncMock()
    fake_variant_id = uuid4()
    with patch("app.modules.catalog.repository.CatalogRepository.find_variant_by_id", return_value=None):
        with pytest.raises(NotFoundError) as exc_info:
            await CatalogService.get_variant(session_mock, fake_variant_id)

        assert str(fake_variant_id) in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_color_not_found_raises_not_found_error():
    """Verify get_color raises NotFoundError when color_id does not exist."""
    session_mock = AsyncMock()
    fake_color_id = uuid4()
    with patch("app.modules.catalog.repository.CatalogRepository.find_color_by_id", return_value=None):
        with pytest.raises(NotFoundError) as exc_info:
            await CatalogService.get_color(session_mock, fake_color_id)

        assert str(fake_color_id) in str(exc_info.value.detail)
