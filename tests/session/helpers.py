from pathlib import Path

import aiosqlite
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


def sample_checkpoint() -> Checkpoint:
    return {
        "v": 4,
        "id": "00000000-0000-0000-0000-000000000001",
        "ts": "2026-01-01T00:00:00+00:00",
        "channel_values": {"messages": []},
        "channel_versions": {"__start__": 1},
        "versions_seen": {"__start__": {"__start__": 1}},
        "updated_channels": ["messages"],
    }


def thread_config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}


async def write_checkpoint(db_path: Path, thread_id: str) -> None:
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        metadata: CheckpointMetadata = {"source": "input", "step": 1, "parents": {}}
        await checkpointer.aput(thread_config(thread_id), sample_checkpoint(), metadata, {})


async def count_checkpoint_rows(db_path: Path) -> tuple[int, int]:
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
