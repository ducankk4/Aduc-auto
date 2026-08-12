"""FastAPI application factory: wires the container, lifespan, middleware,
and centralized exception handling. Mirrors the general shape of
backend/src/app/main.py (lifespan, CORS, exception handler, router
registration under /api/v1) without importing any backend code.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from ai_service.bootstrap.container import build_container
from ai_service.config import get_settings
from ai_service.domain.exceptions import AiServiceError
from ai_service.infrastructure.persistence.checkpointer import build_checkpointer
from ai_service.presentation.api.chat import chat_router
from ai_service.presentation.api.health import health_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with build_checkpointer(settings) as checkpointer:
            app.state.container = await build_container(settings, checkpointer)
            logger.bind(app_env=settings.app_env).info("ai-service started")
            try:
                yield
            finally:
                await app.state.container.backend_client.aclose()
                await app.state.container.retriever.aclose()

    app = FastAPI(title="Aduc Auto - ai-service", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AiServiceError)
    async def ai_service_error_handler(request: Request, exc: AiServiceError) -> JSONResponse:
        logger.bind(code=exc.code, path=request.url.path).error("Request failed: {}", exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.bind(path=request.url.path).exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": "An internal server error occurred."},
            },
        )

    app.include_router(chat_router, prefix=API_PREFIX)
    app.include_router(health_router)

    return app
