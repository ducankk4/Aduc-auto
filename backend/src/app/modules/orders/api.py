"""Orders Module — Presentation Layer (FastAPI Routers for Orders & Admin Management)."""

from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["Deposit Orders"])

# Endpoints will be mounted in Phase 2
