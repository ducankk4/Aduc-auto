"""Catalog Module — Presentation Layer (FastAPI Routers for Public Catalog & Admin CRUD)."""

from fastapi import APIRouter

router = APIRouter(prefix="/catalog", tags=["Vehicle Catalog"])

# Endpoints will be mounted in Phase 2
