"""FastAPI Entry Point — Application Factory & Router Mounting.

Architecture: Modular 3-Layer Monolith
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from app.config import settings
from app.core.database import engine
from app.core.exceptions import AppError
from app.core.logger import setup_logger
from app.core.middlewares import RequestIDMiddleware
from app.modules.users.api import admin_users_router, auth_router
from app.modules.catalog.api import catalog_router
from app.modules.leads.api import leads_router
from app.modules.orders.api import orders_router, admin_orders_router
from app.modules.payments.api import payments_router

# Configure centralized Loguru logger once for the entire application.
# All other modules use: from loguru import logger
setup_logger()



# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Aduc Auto API Platform [env={}, debug={}]", settings.APP_ENV, settings.APP_DEBUG)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception as e:
        logger.error("Database connection failed: {}", e)

    yield

    logger.info("Shutting down Aduc Auto API Platform")
    await engine.dispose()
    logger.info("Engine disposed")



app = FastAPI(
    title="Aduc Auto API Platform",
    description="Modular Monolith Backend for Car Deposit Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ③ Middlewares
app.add_middleware(RequestIDMiddleware)          # ← Gắn X-Request-ID mới thêm
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ④ Global Exception Handler
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.code, "message": exc.detail},
        },
    )

# ⑤ Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_users_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(admin_orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": "aduc-auto-backend"}
