from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from tests.session.helpers import count_checkpoint_rows, write_checkpoint

from zero_agent.command.base import CommandContext
from zero_agent.command.handlers.reset import ResetCommand
from zero_agent.command.router import CommandRouter
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.i18n import I18n
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry


@pytest.fixture
def session_key() -> SessionKey:
    return SessionKey(platform="wecom", chat_id="chat1", user_id="user1")


@pytest.fixture
def command_context(session_key: SessionKey) -> CommandContext:
    return CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(
            platform="wecom",
            content="/reset",
            session_id=session_key.to_id(),
        ),
        args=[],
    )


@pytest.mark.asyncio
async def test_reset_command_calls_registry(session_key: SessionKey, command_context: CommandContext) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.reset = AsyncMock(return_value=f"{session_key.to_id()}:gen2")
    handler = ResetCommand(registry=registry)

    result = await handler.run(command_context)

    registry.reset.assert_awaited_once_with(session_key)
    assert result.message == "已开启新对话，上下文已清空。"


@pytest.mark.asyncio
async def test_reset_command_uses_locale(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.reset = AsyncMock(return_value=session_key.to_id())
    handler = ResetCommand(registry=registry)
    ctx = CommandContext(
        key=session_key,
        locale="en",
        event=MessageEvent(platform="wecom", content="/reset", session_id=session_key.to_id()),
        args=[],
    )

    result = await handler.run(ctx)

    assert result.message == "New conversation started. Context cleared."


@pytest.mark.asyncio
async def test_reset_command_with_custom_i18n(session_key: SessionKey, command_context: CommandContext) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.reset = AsyncMock(return_value=session_key.to_id())
    i18n = I18n(locales={"zh": {"command": {"reset": {"done": "自定义重置文案"}}}, "en": {}})
    handler = ResetCommand(registry=registry, i18n=i18n)

    result = await handler.run(command_context)

    assert result.message == "自定义重置文案"


@pytest.mark.asyncio
async def test_reset_command_via_router(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.reset = AsyncMock(return_value=session_key.to_id())
    router = CommandRouter([ResetCommand(registry=registry)])
    ctx = CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(platform="wecom", content="新对话", session_id=session_key.to_id()),
        args=[],
    )

    matched = router.match("新对话")
    assert matched is not None
    result = await router.dispatch(matched, ctx)

    registry.reset.assert_awaited_once_with(session_key)
    assert result.message == "已开启新对话，上下文已清空。"


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
async def test_reset_command_preserves_checkpoint(
    registry_with_checkpoint: SessionRegistry,
    tmp_path: Path,
    session_key: SessionKey,
) -> None:
    old_thread_id = await registry_with_checkpoint.resolve_thread_id(session_key)
    await write_checkpoint(tmp_path / "checkpoints.db", old_thread_id)
    handler = ResetCommand(registry=registry_with_checkpoint)
    ctx = CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(platform="wecom", content="/reset", session_id=session_key.to_id()),
        args=[],
    )

    await handler.run(ctx)

    assert await count_checkpoint_rows(tmp_path / "checkpoints.db") != (0, 0)
