import asyncio

import pytest

from zero_agent.runner.lifecycle import CronRunner, session_expire_tick
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry


@pytest.mark.asyncio
async def test_cron_runner_invokes_on_tick(tmp_path) -> None:
    tick_count = 0
    done = asyncio.Event()

    async def on_tick() -> None:
        nonlocal tick_count
        tick_count += 1
        done.set()

    runner = CronRunner(interval=1, on_tick=on_tick)
    runner.start()
    await asyncio.wait_for(done.wait(), timeout=3)
    runner.stop()
    assert tick_count >= 1


@pytest.mark.asyncio
async def test_session_expire_tick_calls_registry(tmp_path) -> None:
    registry = SessionRegistry(str(tmp_path / "session.db"))
    await registry.open()
    try:
        key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
        await registry.resolve_thread_id(key)
        tick = session_expire_tick(registry, ttl_seconds=3600)
        await tick()
    finally:
        await registry.close()
