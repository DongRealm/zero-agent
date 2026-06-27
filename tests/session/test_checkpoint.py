from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from tests.session.helpers import count_checkpoint_rows, thread_config, write_checkpoint
from zero_agent.session.checkpoint import CheckpointStore, delete_thread


@pytest.fixture
async def checkpoint_db(tmp_path: Path) -> AsyncIterator[Path]:
    yield tmp_path / "checkpoints.db"


@pytest.mark.asyncio
async def test_delete_thread_clears_checkpoint_rows(checkpoint_db: Path) -> None:
    thread_id = "wecom:chat1:user1"
    await write_checkpoint(checkpoint_db, thread_id)
    assert await count_checkpoint_rows(checkpoint_db) != (0, 0)

    await delete_thread(str(checkpoint_db), thread_id)
    assert await count_checkpoint_rows(checkpoint_db) == (0, 0)


@pytest.mark.asyncio
async def test_checkpoint_store_delete_thread(checkpoint_db: Path) -> None:
    thread_id = "wecom:chat2"
    await write_checkpoint(checkpoint_db, thread_id)

    async with CheckpointStore(str(checkpoint_db)) as store:
        config = thread_config(thread_id)
        listed = [item async for item in store.saver.alist(config)]
        assert len(listed) == 1
        await store.delete_thread(thread_id)
        listed_after = [item async for item in store.saver.alist(config)]
        assert listed_after == []

    assert await count_checkpoint_rows(checkpoint_db) == (0, 0)
