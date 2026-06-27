import pytest

from zero_agent.command import CommandRouter, HelpCommand, LangCommand, ResetCommand
from zero_agent.command.handlers.help import HELP_NAMES, build_help_message, format_command_triggers
from zero_agent.i18n import I18n


def test_help_names() -> None:
    assert "/help" in HELP_NAMES
    assert "帮助" in HELP_NAMES


def test_format_command_triggers_puts_slash_first() -> None:
    text = format_command_triggers(frozenset({"/reset", "重置", "/new"}))
    assert text.startswith("/new、/reset")
    assert "重置" in text


def test_build_help_message_lists_registered_handlers() -> None:
    from unittest.mock import MagicMock

    reset = MagicMock()
    reset.names = frozenset({"/reset", "重置"})
    reset.description_key = "command.reset.description"
    lang = MagicMock()
    lang.names = frozenset({"/lang"})
    lang.description_key = "command.lang.description"
    router = CommandRouter([reset, lang])

    message = build_help_message(router, I18n(), "zh")

    assert "可用命令" in message
    assert "/reset" in message
    assert "/lang" in message
    assert "开启新对话" in message
    assert "切换语言" in message


@pytest.mark.asyncio
async def test_help_returns_zh_body(tmp_path) -> None:
    from zero_agent.command.base import CommandContext
    from zero_agent.gateway.protocol import MessageEvent
    from zero_agent.session.models import SessionKey
    from zero_agent.session.registry import SessionRegistry

    registry = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await registry.open()
    try:
        router = CommandRouter(
            [
                ResetCommand(registry),
                LangCommand(registry),
            ]
        )
        router.register(HelpCommand(router))
        command = HelpCommand(router)
        ctx = CommandContext(
            key=SessionKey(platform="wecom", chat_id="c1", user_id="u1"),
            locale="zh",
            event=MessageEvent(platform="wecom", content="/help", session_id="wecom:c1:u1"),
            args=[],
        )

        result = await command.run(ctx)

        assert "/reset" in result.message
        assert "/lang" in result.message
        assert "/help" in result.message
        assert "开启新对话" in result.message
    finally:
        await registry.close()


@pytest.mark.asyncio
async def test_help_returns_en_body(tmp_path) -> None:
    from zero_agent.command.base import CommandContext
    from zero_agent.gateway.protocol import MessageEvent
    from zero_agent.session.models import SessionKey
    from zero_agent.session.registry import SessionRegistry

    registry = SessionRegistry(str(tmp_path / "session.db"), default_locale="en")
    await registry.open()
    try:
        router = CommandRouter(
            [
                ResetCommand(registry),
                LangCommand(registry),
            ]
        )
        router.register(HelpCommand(router))
        command = HelpCommand(router)
        ctx = CommandContext(
            key=SessionKey(platform="wecom", chat_id="c1"),
            locale="en",
            event=MessageEvent(platform="wecom", content="/help"),
            args=[],
        )

        result = await command.run(ctx)

        assert "Available commands" in result.message
        assert "/reset" in result.message
        assert "Start a new conversation" in result.message
    finally:
        await registry.close()
