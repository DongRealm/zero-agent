"""Structured logging and tracing helpers."""

import structlog

from zero_agent.observability.callbacks import AgentLoggingCallback
from zero_agent.observability.context import bind_thread_id, message_context
from zero_agent.observability.setup import configure_logging, get_logger

bind_contextvars = structlog.contextvars.bind_contextvars
clear_contextvars = structlog.contextvars.clear_contextvars

__all__ = [
    "AgentLoggingCallback",
    "bind_contextvars",
    "bind_thread_id",
    "clear_contextvars",
    "configure_logging",
    "get_logger",
    "message_context",
]
