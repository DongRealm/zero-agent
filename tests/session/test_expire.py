from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite
import pytest

from tests.session.helpers import count_checkpoint_rows, write_checkpoint
from zero_agent.session.models import SessionKey, ThreadStatus
from zero_agent.session.registry import SessionRegistry


async def set_thread_ended_at(db_path: Path, thread_id: str, ended_at: datetime) -> None:
    conn = await aiosqlite.connect(db_path)
    try:
        await conn.execute(
            "UPDATE session_threads SET ended_at = ? WHERE thread_id = ?",
            (ended_at.isoformat(), thread_id),
        )
        await conn.commit()
    finally:
        await conn.close()


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
async def test_expire_stale_purges_old_closed_thread(
    registry_with_checkpoint: SessionRegistry,
    tmp_path: Path,
) -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    old_thread_id = await registry_with_checkpoint.resolve_thread_id(key)
    checkpoint_db = tmp_path / "checkpoints.db"
    await write_checkpoint(checkpoint_db, old_thread_id)
    assert await count_checkpoint_rows(checkpoint_db) != (0, 0)

    await registry_with_checkpoint.reset(key)
    old_ended_at = datetime.now(UTC) - timedelta(days=8)
    await set_thread_ended_at(tmp_path / "session.db", old_thread_id, old_ended_at)

    purged = await registry_with_checkpoint.expire_stale(
        ttl_seconds=7 * 24 * 3600,
        now=datetime.now(UTC),
    )
    assert purged == [old_thread_id]
    assert await count_checkpoint_rows(checkpoint_db) == (0, 0)

    threads = await registry_with_checkpoint.list_threads(key)
    assert all(thread.thread_id != old_thread_id for thread in threads)
    assert any(thread.status == ThreadStatus.ACTIVE for thread in threads)


@pytest.mark.asyncio
async def test_expire_stale_preserves_recent_closed_thread(
    registry_with_checkpoint: SessionRegistry,
    tmp_path: Path,
) -> None:
    key = SessionKey(platform="wecom", chat_id="chat2", user_id="user2")
    old_thread_id = await registry_with_checkpoint.resolve_thread_id(key)
    await write_checkpoint(tmp_path / "checkpoints.db", old_thread_id)
    await registry_with_checkpoint.reset(key)

    purged = await registry_with_checkpoint.expire_stale(
        ttl_seconds=7 * 24 * 3600,
        now=datetime.now(UTC),
    )
    assert purged == []
    assert await count_checkpoint_rows(tmp_path / "checkpoints.db") != (0, 0)

    threads = await registry_with_checkpoint.list_threads(key)
    assert any(thread.thread_id == old_thread_id for thread in threads)


@pytest.mark.asyncio
async def test_expire_stale_skips_active_thread(
    registry_with_checkpoint: SessionRegistry,
    tmp_path: Path,
) -> None:
    key = SessionKey(platform="wecom", chat_id="chat3", user_id="user3")
    active_thread_id = await registry_with_checkpoint.resolve_thread_id(key)
    await write_checkpoint(tmp_path / "checkpoints.db", active_thread_id)
    old_ended_at = datetime.now(UTC) - timedelta(days=30)
    await set_thread_ended_at(tmp_path / "session.db", active_thread_id, old_ended_at)

    purged = await registry_with_checkpoint.expire_stale(
        ttl_seconds=3600,
        now=datetime.now(UTC),
    )
    assert purged == []
    assert await count_checkpoint_rows(tmp_path / "checkpoints.db") != (0, 0)


@pytest.mark.asyncio
async def test_expire_stale_noop_for_zero_ttl(registry_with_checkpoint: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat4", user_id="user4")
    await registry_with_checkpoint.resolve_thread_id(key)
    await registry_with_checkpoint.reset(key)

    purged = await registry_with_checkpoint.expire_stale(ttl_seconds=0)
    assert purged == []
