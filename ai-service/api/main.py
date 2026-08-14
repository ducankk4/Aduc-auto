"""FastAPI entry point for ai-service.

Heavy resources (embedding model, supervisor graph, SQLite checkpointer)
are built exactly once in the lifespan and shared across requests via
app.state.

Run:  uv run uvicorn api.main:app --reload --port 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from api.routes.chat import chat_router
from api.routes.conversation import conversation_router
from api.dependencies import build_message_service, build_supervisor
from api.response import error
from agent.checkpointer import open_checkpointer
from core.config import settings
from core.exceptions import AIServiceError
from core.logger import setup_logger

setup_logger()

_STATUS_BY_CODE = {
    "NOT_FOUND": 404,
    "DOMAIN_ERROR": 422,
    "APPROVAL_REJECTED": 409,
    "INFRASTRUCTURE_ERROR": 502,
    "AI_SERVICE_ERROR": 500,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the checkpointer and build the wired supervisor once per process."""
    logger.info("Starting ai-service [env={}, debug={}]", settings.APP_ENV, settings.APP_DEBUG)
    async with open_checkpointer() as checkpointer:
        app.state.supervisor = build_supervisor(checkpointer)
        app.state.message_service = await build_message_service()
        logger.info("Supervisor ready")
        yield
    logger.info("ai-service shut down")


app = FastAPI(
    title="Aduc Auto AI Service",
    description="Supervisor agent (RAG + subagents) for the car deposit platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError) -> JSONResponse:
    """Map the framework-free exception hierarchy onto HTTP responses."""
    status_code = _STATUS_BY_CODE.get(exc.code, 500)
    logger.error("Request failed [code={}, status={}]: {}", exc.code, status_code, exc.message)
    return error(code=exc.code, message=exc.message, status_code=status_code)


app.include_router(chat_router, prefix="/api/v1")
app.include_router(conversation_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "app": "aduc-auto-ai-service"}
