import pytest

from zero_agent.command.base import CommandContext, CommandResult
from zero_agent.command.router import CommandRouter, normalize_command_text
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.session.models import SessionKey


class StubLangCommand:
    names = frozenset({"/lang", "/语言"})
    description_key = "command.lang.description"

    async def run(self, ctx: CommandContext) -> CommandResult:
        locale = ctx.args[0] if ctx.args else "unknown"
        return CommandResult(message=f"lang:{locale}")


class StubResetCommand:
    names = frozenset({"/reset", "/new", "重置", "新对话"})
    description_key = "command.reset.description"

    async def run(self, _ctx: CommandContext) -> CommandResult:
        return CommandResult(message="reset:ok")


@pytest.fixture
def router() -> CommandRouter:
    return CommandRouter([StubResetCommand(), StubLangCommand()])


def test_normalize_strips_whitespace() -> None:
    assert normalize_command_text("  /reset  ") == "/reset"


def test_normalize_strips_at_prefix() -> None:
    assert normalize_command_text("@ZeroAgent /reset") == "/reset"
    assert normalize_command_text("@bot  重置") == "重置"


def test_match_reset_slash(router: CommandRouter) -> None:
    matched = router.match("/reset")
    assert matched is not None
    assert matched.trigger == "/reset"
    assert matched.args == []


def test_match_reset_aliases(router: CommandRouter) -> None:
    assert router.match("新对话") is not None
    assert router.match("/new") is not None
    assert router.match("重置") is not None


def test_match_with_at_prefix(router: CommandRouter) -> None:
    matched = router.match("@MyBot /reset")
    assert matched is not None
    assert matched.trigger == "/reset"


def test_match_lang_with_args(router: CommandRouter) -> None:
    matched = router.match("/lang en")
    assert matched is not None
    assert matched.trigger == "/lang"
    assert matched.args == ["en"]

    matched_zh = router.match("/语言 中文")
    assert matched_zh is not None
    assert matched_zh.trigger == "/语言"
    assert matched_zh.args == ["中文"]


def test_match_returns_none_for_unknown(router: CommandRouter) -> None:
    assert router.match("hello") is None
    assert router.match("@bot") is None
    assert router.match("") is None


@pytest.mark.asyncio
async def test_dispatch_passes_args(router: CommandRouter) -> None:
    matched = router.match("/lang zh")
    assert matched is not None
    ctx = CommandContext(
        key=SessionKey(platform="wecom", chat_id="c1", user_id="u1"),
        locale="zh",
        event=MessageEvent(platform="wecom", content="/lang zh", session_id="wecom:c1:u1"),
        args=[],
    )
    result = await router.dispatch(matched, ctx)
    assert result.message == "lang:zh"


@pytest.mark.asyncio
async def test_dispatch_reset(router: CommandRouter) -> None:
    matched = router.match("/reset")
    assert matched is not None
    ctx = CommandContext(
        key=SessionKey(platform="wecom", chat_id="c1"),
        locale="zh",
        event=MessageEvent(platform="wecom", content="/reset"),
        args=[],
    )
    result = await router.dispatch(matched, ctx)
    assert result.message == "reset:ok"
