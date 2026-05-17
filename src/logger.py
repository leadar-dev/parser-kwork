from __future__ import annotations

from typing import Any

import structlog

from .config import cfg

_LEVEL_MAP: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    level = _LEVEL_MAP.get(cfg.logging.level.upper(), 20)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.ExceptionRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger() -> Any:  # structlog.BoundLogger — нет публичного типа
    _configure()
    return structlog.get_logger()
