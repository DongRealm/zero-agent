from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from zero_agent.session.checkpoint import CheckpointStore, delete_thread


def _thread_config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}


def _sample_checkpoint() -> Checkpoint:
    return {
        "v": 4,
        "id": "00000000-0000-0000-0000-000000000001",
        "ts": "2026-01-01T00:00:00+00:00",
        "channel_values": {"messages": []},
        "channel_versions": {"__start__": 1},
        "versions_seen": {"__start__": {"__start__": 1}},
        "updated_channels": ["messages"],
    }


async def _write_checkpoint(db_path: Path, thread_id: str) -> None:
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        config = _thread_config(thread_id)
        metadata: CheckpointMetadata = {"source": "input", "step": 1, "parents": {}}
        await checkpointer.aput(config, _sample_checkpoint(), metadata, {})


async def _count_rows(db_path: Path) -> tuple[int, int]:
    conn = await aiosqlite.connect(db_path)
    try:
        checkpoints = await conn.execute("SELECT COUNT(*) FROM checkpoints")
        writes = await conn.execute("SELECT COUNT(*) FROM writes")
        cp_row = await checkpoints.fetchone()
        wr_row = await writes.fetchone()
        assert cp_row is not None and wr_row is not None
        return int(cp_row[0]), int(wr_row[0])
    finally:
        await conn.close()


@pytest.fixture
async def checkpoint_db(tmp_path: Path) -> AsyncIterator[Path]:
    yield tmp_path / "checkpoints.db"


@pytest.mark.asyncio
async def test_delete_thread_clears_checkpoint_rows(checkpoint_db: Path) -> None:
    thread_id = "wecom:chat1:user1"
    await _write_checkpoint(checkpoint_db, thread_id)
    assert await _count_rows(checkpoint_db) != (0, 0)

    await delete_thread(str(checkpoint_db), thread_id)
    assert await _count_rows(checkpoint_db) == (0, 0)


@pytest.mark.asyncio
async def test_checkpoint_store_delete_thread(checkpoint_db: Path) -> None:
    thread_id = "wecom:chat2"
    await _write_checkpoint(checkpoint_db, thread_id)

    async with CheckpointStore(str(checkpoint_db)) as store:
        config = _thread_config(thread_id)
        listed = [item async for item in store.saver.alist(config)]
        assert len(listed) == 1
        await store.delete_thread(thread_id)
        listed_after = [item async for item in store.saver.alist(config)]
        assert listed_after == []

    assert await _count_rows(checkpoint_db) == (0, 0)
