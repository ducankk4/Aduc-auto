"""Pytest Configuration & Fixtures (Async DB Session, Test Client)."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
