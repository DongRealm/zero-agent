"""Request-scoped logging context for session and thread correlation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import structlog

bind_contextvars = structlog.contextvars.bind_contextvars
clear_contextvars = structlog.contextvars.clear_contextvars


@contextmanager
def message_context(*, session_key: str, thread_id: str | None = None) -> Iterator[None]:
    """Bind ``session_key`` and optional ``thread_id`` for the current async task."""
    clear_contextvars()
    fields: dict[str, str] = {"session_key": session_key}
    if thread_id is not None:
        fields["thread_id"] = thread_id
    bind_contextvars(**fields)
    try:
        yield
    finally:
        clear_contextvars()


def bind_thread_id(thread_id: str) -> None:
    """Update ``thread_id`` in the current logging context."""
    bind_contextvars(thread_id=thread_id)
