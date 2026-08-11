"""Unprefixed health check endpoint, mirroring backend's convention."""

from __future__ import annotations

from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": "ai-service"}
