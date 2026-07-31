"""Centralized Loguru configuration for the entire application.

Call `setup_logger()` once at startup (in main.py lifespan).
All other modules simply use: from loguru import logger
"""

import sys
import logging

from loguru import logger

from app.config import settings


def setup_logger() -> None:
    """Configure Loguru as the application-wide logging backend.

    - Replaces the default Loguru handler with a structured stdout sink.
    - Intercepts stdlib logging (SQLAlchemy, Uvicorn, third-party libs)
      and routes all records through Loguru so the entire system shares
      one consistent format and level.
    - Log level is driven by APP_DEBUG: DEBUG in development, INFO in production.
    """
    log_level = "DEBUG" if settings.APP_DEBUG else "INFO"

    logger.remove()

    # Reconfigure stdout encoding to UTF-8 in-place.
    # Using reconfigure() (instead of wrapping with TextIOWrapper) preserves
    # isatty() so Loguru can detect the terminal and render colors correctly.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=settings.APP_DEBUG,
    )

    _intercept_stdlib_logging()

    logger.info("Logger configured [level={}]", log_level)


def _intercept_stdlib_logging() -> None:
    """Route all stdlib logging records through Loguru.

    Libraries such as SQLAlchemy, Uvicorn, and python-jose use stdlib
    logging internally. This intercept handler ensures their output is
    formatted and filtered by Loguru alongside application logs.
    """

    class _InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level: str | int = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back  # type: ignore[assignment]
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
