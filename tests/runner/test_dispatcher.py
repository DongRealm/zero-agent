from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from zero_agent.agent.types import AgentError, AgentResult
from zero_agent.command import CommandRouter, HelpCommand, LangCommand, ResetCommand
from zero_agent.gateway.outbound import AdapterCapabilities
from zero_agent.gateway.protocol import MessageEvent, PushTarget
from zero_agent.runner.dispatcher import MessageDispatcher
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry


@pytest.fixture
async def registry(tmp_path: Path) -> AsyncIterator[SessionRegistry]:
    reg = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await reg.open()
    yield reg
    await reg.close()


@pytest.fixture
def session_key() -> SessionKey:
    return SessionKey(platform="wecom", chat_id="chat1", user_id="user1")


@pytest.fixture
def agent() -> AsyncMock:
    mock = AsyncMock()
    mock.invoke = AsyncMock(return_value=AgentResult(content="agent-reply", thread_id="thread-1"))
    return mock


@pytest.fixture
def dispatcher(registry: SessionRegistry, agent: AsyncMock) -> MessageDispatcher:
    commands = CommandRouter(
        [
            ResetCommand(registry),
            LangCommand(registry),
        ]
    )
    commands.register(HelpCommand(commands))
    return MessageDispatcher(registry, commands, agent)


@pytest.mark.asyncio
async def test_dispatcher_reset_replies_via_outbound(
    dispatcher: MessageDispatcher,
    session_key: SessionKey,
) -> None:
    outbound = AsyncMock()
    outbound.reply = AsyncMock()
    event = MessageEvent(
        platform="wecom",
        content="/reset",
        session_id=session_key.to_id(),
        push_target=PushTarget(chat_id="chat1"),
        reply_to={"body": {"chatid": "chat1"}},
    )

    await dispatcher.handle(event, outbound)

    outbound.reply.assert_awaited_once_with(event, "已开启新对话，上下文已清空。")


@pytest.mark.asyncio
async def test_dispatcher_lang_replies_via_outbound(
    dispatcher: MessageDispatcher,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    outbound = AsyncMock()
    outbound.reply = AsyncMock()
    event = MessageEvent(
        platform="wecom",
        content="/lang en",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    outbound.reply.assert_awaited_once()
    assert outbound.reply.await_args.args[1] == "Language switched to English."
    assert await registry.get_locale(session_key) == "en"


@pytest.mark.asyncio
async def test_dispatcher_agent_invoke_replies_via_outbound(
    dispatcher: MessageDispatcher,
    agent: AsyncMock,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    outbound = AsyncMock()
    outbound.reply = AsyncMock()
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    thread_id = await registry.resolve_thread_id(session_key)
    agent.invoke.assert_awaited_once_with(thread_id, "hello", user_id="user1")
    outbound.reply.assert_awaited_once_with(event, "agent-reply")


@pytest.mark.asyncio
async def test_dispatcher_agent_error_replies_with_i18n(
    dispatcher: MessageDispatcher,
    agent: AsyncMock,
    session_key: SessionKey,
) -> None:
    agent.invoke.side_effect = AgentError("boom", thread_id="thread-1")
    outbound = AsyncMock()
    outbound.reply = AsyncMock()
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    outbound.reply.assert_awaited_once()
    assert outbound.reply.await_args.args[1] == "处理失败，请稍后重试或发送 /reset 重新开始。"


@pytest.mark.asyncio
async def test_dispatcher_agent_error_uses_session_locale(
    dispatcher: MessageDispatcher,
    agent: AsyncMock,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    await registry.set_locale(session_key, "en")
    agent.invoke.side_effect = AgentError("boom", thread_id="thread-1")
    outbound = AsyncMock()
    outbound.reply = AsyncMock()
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    assert (
        outbound.reply.await_args.args[1]
        == "Something went wrong. Please retry or send /reset to start over."
    )


def _streaming_outbound() -> AsyncMock:
    outbound = AsyncMock()
    outbound.capabilities = AdapterCapabilities(reply=True, reply_stream=True)
    outbound.reply = AsyncMock()
    outbound.reply_stream = AsyncMock()
    return outbound


@pytest.mark.asyncio
async def test_dispatcher_agent_uses_reply_stream_when_supported(
    dispatcher: MessageDispatcher,
    agent: AsyncMock,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    outbound = _streaming_outbound()
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    thread_id = await registry.resolve_thread_id(session_key)
    agent.invoke.assert_awaited_once_with(thread_id, "hello", user_id="user1")
    assert outbound.reply_stream.await_count == 2
    outbound.reply_stream.assert_any_await(event, thread_id, "处理中…", finish=False)
    outbound.reply_stream.assert_awaited_with(event, thread_id, "agent-reply", finish=True)
    outbound.reply.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatcher_agent_stream_thinking_uses_locale(
    dispatcher: MessageDispatcher,
    agent: AsyncMock,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    await registry.set_locale(session_key, "en")
    outbound = _streaming_outbound()
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    thread_id = await registry.resolve_thread_id(session_key)
    agent.invoke.assert_awaited_once()
    outbound.reply_stream.assert_any_await(event, thread_id, "Working on it…", finish=False)


@pytest.mark.asyncio
async def test_dispatcher_agent_stream_error_finishes_with_i18n(
    dispatcher: MessageDispatcher,
    agent: AsyncMock,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    agent.invoke.side_effect = AgentError("boom", thread_id="thread-1")
    outbound = _streaming_outbound()
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    thread_id = await registry.resolve_thread_id(session_key)
    assert outbound.reply_stream.await_count == 2
    outbound.reply_stream.assert_awaited_with(
        event,
        thread_id,
        "处理失败，请稍后重试或发送 /reset 重新开始。",
        finish=True,
    )


@pytest.mark.asyncio
async def test_dispatcher_help_replies_via_outbound(
    dispatcher: MessageDispatcher,
    session_key: SessionKey,
) -> None:
    outbound = AsyncMock()
    outbound.reply = AsyncMock()
    event = MessageEvent(
        platform="wecom",
        content="/help",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    outbound.reply.assert_awaited_once()
    assert "/reset" in outbound.reply.await_args.args[1]
    assert "/lang" in outbound.reply.await_args.args[1]


@pytest.mark.asyncio
async def test_dispatcher_stream_recovers_when_finish_fails(
    dispatcher: MessageDispatcher,
    session_key: SessionKey,
    registry: SessionRegistry,
) -> None:
    outbound = _streaming_outbound()
    outbound.reply_stream = AsyncMock(
        side_effect=[
            None,
            RuntimeError("finish failed"),
            None,
        ]
    )
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    thread_id = await registry.resolve_thread_id(session_key)
    assert outbound.reply_stream.await_count == 3
    outbound.reply_stream.assert_any_await(event, thread_id, "处理中…", finish=False)
    outbound.reply_stream.assert_any_await(
        event,
        thread_id,
        "agent-reply",
        finish=True,
    )
    outbound.reply_stream.assert_awaited_with(
        event,
        thread_id,
        "处理失败，请稍后重试或发送 /reset 重新开始。",
        finish=True,
    )


@pytest.mark.asyncio
async def test_dispatcher_stream_recovers_via_reply_when_stream_finish_fails_twice(
    dispatcher: MessageDispatcher,
    session_key: SessionKey,
) -> None:
    outbound = _streaming_outbound()
    outbound.reply_stream = AsyncMock(
        side_effect=[
            None,
            RuntimeError("finish failed"),
            RuntimeError("recover failed"),
        ]
    )
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=session_key.to_id(),
    )

    await dispatcher.handle(event, outbound)

    outbound.reply.assert_awaited_once_with(
        event,
        "处理失败，请稍后重试或发送 /reset 重新开始。",
    )
