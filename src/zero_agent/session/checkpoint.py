"""LangGraph checkpoint storage helpers."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


class CheckpointStore:
    """Wraps LangGraph ``AsyncSqliteSaver`` for checkpoint persistence."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._context: Any = None
        self._saver: AsyncSqliteSaver | None = None

    async def __aenter__(self) -> Self:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._context = AsyncSqliteSaver.from_conn_string(self._db_path)
        self._saver = await self._context.__aenter__()
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
        self._saver = None

    @property
    def saver(self) -> AsyncSqliteSaver:
        if self._saver is None:
            raise RuntimeError("CheckpointStore is not open")
        return self._saver

    async def delete_thread(self, thread_id: str) -> None:
        await self.saver.adelete_thread(thread_id)


async def delete_thread(checkpoint_db_path: str, thread_id: str) -> None:
    """Delete all checkpoint data for a thread."""
    async with AsyncSqliteSaver.from_conn_string(checkpoint_db_path) as checkpointer:
        await checkpointer.adelete_thread(thread_id)
