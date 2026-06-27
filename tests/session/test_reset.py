from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from tests.session.helpers import count_checkpoint_rows, write_checkpoint
from zero_agent.session.models import SessionKey, ThreadStatus
from zero_agent.session.registry import SessionRegistry, thread_id_for


@pytest.fixture
async def registry(tmp_path: Path) -> AsyncIterator[SessionRegistry]:
    reg = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await reg.open()
    yield reg
    await reg.close()


@pytest.fixture
async def registry_with_checkpoint(tmp_path: Path) -> AsyncIterator[SessionRegistry]:
    reg = SessionRegistry(
        str(tmp_path / "session.db"),
        default_locale="zh",
        checkpoint_db_path=str(tmp_path / "checkpoints.db"),
    )
    await reg.open()
    yield reg
    await reg.close()


@pytest.mark.asyncio
async def test_reset_creates_initial_thread(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    thread_id = await registry.reset(key)
    assert thread_id == thread_id_for(key, 1)

    record = await registry.get_record(key)
    assert record is not None
    assert record.generation == 1
    assert record.active_thread_id == thread_id

    threads = await registry.list_threads(key)
    assert len(threads) == 1
    assert threads[0].status == ThreadStatus.ACTIVE


@pytest.mark.asyncio
async def test_reset_rotates_thread_id(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    first = await registry.resolve_thread_id(key)
    assert first == thread_id_for(key, 1)

    second = await registry.reset(key)
    assert second == thread_id_for(key, 2)
    assert second != first

    record = await registry.get_record(key)
    assert record is not None
    assert record.generation == 2
    assert record.active_thread_id == second

    third = await registry.resolve_thread_id(key)
    assert third == second

    threads = await registry.list_threads(key)
    assert len(threads) == 2
    assert threads[0].thread_id == first
    assert threads[0].status == ThreadStatus.CLOSED
    assert threads[0].ended_at is not None
    assert threads[1].thread_id == second
    assert threads[1].status == ThreadStatus.ACTIVE


@pytest.mark.asyncio
async def test_reset_preserves_old_checkpoint(
    registry_with_checkpoint: SessionRegistry,
    tmp_path: Path,
) -> None:
    key = SessionKey(platform="wecom", chat_id="chat2", user_id="user2")
    old_thread_id = await registry_with_checkpoint.resolve_thread_id(key)
    checkpoint_db = tmp_path / "checkpoints.db"
    await write_checkpoint(checkpoint_db, old_thread_id)
    assert await count_checkpoint_rows(checkpoint_db) != (0, 0)

    new_thread_id = await registry_with_checkpoint.reset(key)
    assert new_thread_id != old_thread_id
    assert await count_checkpoint_rows(checkpoint_db) != (0, 0)

    threads = await registry_with_checkpoint.list_threads(key)
    assert threads[0].thread_id == old_thread_id
    assert threads[0].status == ThreadStatus.CLOSED
