"""LangGraph Store for cross-thread agent memory."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

from langgraph.store.base import BaseStore
from langgraph.store.sqlite.aio import AsyncSqliteStore


class AgentStore:
    """Wraps ``AsyncSqliteStore`` for Deep Agents long-term memory."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._context: Any = None
        self._store: AsyncSqliteStore | None = None

    async def __aenter__(self) -> Self:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._context = AsyncSqliteStore.from_conn_string(self._db_path)
        store = await self._context.__aenter__()
        if store is None:
            raise RuntimeError("Failed to open AgentStore")
        await store.setup()
        self._store = store
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._context is not None:
            await self._context.__aexit__(exc_type, exc, tb)
        self._context = None
        self._store = None

    @property
    def store(self) -> BaseStore:
        if self._store is None:
            raise RuntimeError("AgentStore is not open")
        return self._store
