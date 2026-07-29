"""FastAPI Entry Point — Application Factory & Router Mounting.

Architecture: Modular 3-Layer Monolith
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.users.api import admin_users_router, auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application Lifespan Events (Startup & Shutdown)."""
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI Instance."""
    app = FastAPI(
        title="Aduc Auto API Platform",
        description="Modular Monolith Backend for Car Deposit Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register V1 Routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_users_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "app": "aduc-auto-backend"}

    return app


app = create_app()
