"""Structured logging and tracing helpers."""

import structlog

from zero_agent.observability.setup import configure_logging, get_logger

bind_contextvars = structlog.contextvars.bind_contextvars
clear_contextvars = structlog.contextvars.clear_contextvars

__all__ = [
    "bind_contextvars",
    "clear_contextvars",
    "configure_logging",
    "get_logger",
]
