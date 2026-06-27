from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry


@pytest.fixture
async def registry(tmp_path: Path) -> AsyncIterator[SessionRegistry]:
    reg = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await reg.open()
    yield reg
    await reg.close()


@pytest.mark.asyncio
async def test_resolve_thread_id_creates_record(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    thread_id = await registry.resolve_thread_id(key)
    assert thread_id == "wecom:chat1:user1"

    record = await registry.get_record(key)
    assert record is not None
    assert record.thread_id == thread_id
    assert record.locale == "zh"
    assert record.last_active_at is not None


@pytest.mark.asyncio
async def test_resolve_thread_id_returns_existing(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    first = await registry.resolve_thread_id(key)
    second = await registry.resolve_thread_id(key)
    assert first == second


@pytest.mark.asyncio
async def test_touch_updates_last_active(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat2")
    await registry.resolve_thread_id(key)
    before = await registry.get_record(key)
    assert before is not None

    await registry.touch(key)
    after = await registry.get_record(key)
    assert after is not None
    assert after.last_active_at is not None
    if before.last_active_at is not None:
        assert after.last_active_at >= before.last_active_at


@pytest.mark.asyncio
async def test_get_locale_default(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat3")
    assert await registry.get_locale(key) == "zh"


@pytest.mark.asyncio
async def test_set_locale_persists(registry: SessionRegistry) -> None:
    key = SessionKey(platform="wecom", chat_id="chat4", user_id="user4")
    await registry.set_locale(key, "en")
    assert await registry.get_locale(key) == "en"

    record = await registry.get_record(key)
    assert record is not None
    assert record.locale == "en"
    assert record.thread_id == key.to_id()
