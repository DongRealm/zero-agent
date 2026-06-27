from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from zero_agent.command.base import CommandContext
from zero_agent.command.handlers.lang import LangCommand, parse_lang_arg
from zero_agent.command.router import CommandRouter
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry


@pytest.fixture
def session_key() -> SessionKey:
    return SessionKey(platform="wecom", chat_id="chat2", user_id="user2")


def test_parse_lang_arg_aliases() -> None:
    assert parse_lang_arg("zh") == "zh"
    assert parse_lang_arg("en") == "en"
    assert parse_lang_arg("中文") == "zh"
    assert parse_lang_arg("英文") == "en"
    assert parse_lang_arg("invalid") is None


@pytest.mark.asyncio
async def test_lang_command_sets_locale(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.set_locale = AsyncMock()
    handler = LangCommand(registry=registry)
    ctx = CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(platform="wecom", content="/lang en", session_id=session_key.to_id()),
        args=["en"],
    )

    result = await handler.run(ctx)

    registry.set_locale.assert_awaited_once_with(session_key, "en")
    assert result.message == "Language switched to English."


@pytest.mark.asyncio
async def test_lang_command_chinese_trigger(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.set_locale = AsyncMock()
    handler = LangCommand(registry=registry)
    ctx = CommandContext(
        key=session_key,
        locale="en",
        event=MessageEvent(platform="wecom", content="/语言 中文", session_id=session_key.to_id()),
        args=["中文"],
    )

    result = await handler.run(ctx)

    registry.set_locale.assert_awaited_once_with(session_key, "zh")
    assert result.message == "语言已切换为中文。"


@pytest.mark.asyncio
async def test_lang_command_invalid_arg(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    handler = LangCommand(registry=registry)
    ctx = CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(platform="wecom", content="/lang fr", session_id=session_key.to_id()),
        args=["fr"],
    )

    result = await handler.run(ctx)

    registry.set_locale.assert_not_called()
    assert result.message == "用法：/lang zh 或 /lang en"


@pytest.mark.asyncio
async def test_lang_command_missing_arg(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    handler = LangCommand(registry=registry)
    ctx = CommandContext(
        key=session_key,
        locale="en",
        event=MessageEvent(platform="wecom", content="/lang", session_id=session_key.to_id()),
        args=[],
    )

    result = await handler.run(ctx)

    registry.set_locale.assert_not_called()
    assert result.message == "Usage: /lang zh or /lang en"


@pytest.mark.asyncio
async def test_lang_command_via_router(session_key: SessionKey) -> None:
    registry = AsyncMock(spec=SessionRegistry)
    registry.set_locale = AsyncMock()
    router = CommandRouter([LangCommand(registry=registry)])
    ctx = CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(platform="wecom", content="/lang en", session_id=session_key.to_id()),
        args=[],
    )

    matched = router.match("/lang en")
    assert matched is not None
    assert matched.args == ["en"]
    result = await router.dispatch(matched, ctx)

    registry.set_locale.assert_awaited_once_with(session_key, "en")
    assert result.message == "Language switched to English."


@pytest.fixture
async def registry(tmp_path: Path) -> AsyncIterator[SessionRegistry]:
    reg = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await reg.open()
    yield reg
    await reg.close()


@pytest.mark.asyncio
async def test_lang_command_persists_locale(registry: SessionRegistry, session_key: SessionKey) -> None:
    handler = LangCommand(registry=registry)
    ctx = CommandContext(
        key=session_key,
        locale="zh",
        event=MessageEvent(platform="wecom", content="/lang en", session_id=session_key.to_id()),
        args=["en"],
    )

    await handler.run(ctx)

    assert await registry.get_locale(session_key) == "en"
