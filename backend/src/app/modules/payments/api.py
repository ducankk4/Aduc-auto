"""Payments Module — Presentation Layer (FastAPI Routers for Payment Init & Webhook Callback)."""

from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["Payments Integration"])

# Endpoints will be mounted in Phase 2
