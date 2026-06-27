from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from zero_agent.gateway.outbound import (
    AdapterCapabilities,
    ApprovalRequest,
)
from zero_agent.gateway.platforms.wecom import WecomAdapter, message_event_from_frame
from zero_agent.gateway.protocol import PushTarget


def test_adapter_capabilities_defaults() -> None:
    caps = AdapterCapabilities()
    assert caps.reply is True
    assert caps.reply_stream is False
    assert caps.push is False
    assert caps.approval_card is False
    assert caps.approval_card_update is False


def test_approval_request_fields() -> None:
    req = ApprovalRequest(request_id="r1", title="Approve?", description="details")
    assert req.request_id == "r1"
    assert req.title == "Approve?"
    assert req.description == "details"


def test_wecom_adapter_capabilities() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    assert adapter.capabilities == AdapterCapabilities(reply=True, reply_stream=True, push=True)


@pytest.mark.asyncio
async def test_wecom_reply_uses_reply_to() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    adapter._client = AsyncMock()
    adapter._client.reply = AsyncMock()

    frame = {"body": {"chatid": "chat1", "text": {"content": "hello"}}}
    event = message_event_from_frame(frame)

    await adapter.reply(event, "pong")

    adapter._client.reply.assert_awaited_once_with(
        frame,
        {"msgtype": "markdown", "markdown": {"content": "pong"}},
    )


@pytest.mark.asyncio
async def test_wecom_reply_stream_uses_reply_to() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    adapter._client = AsyncMock()
    adapter._client.reply_stream = AsyncMock()

    frame = {"body": {"chatid": "chat1", "text": {"content": "hello"}}}
    event = message_event_from_frame(frame)

    await adapter.reply_stream(event, "stream-1", "处理中…", finish=False)

    adapter._client.reply_stream.assert_awaited_once_with(
        frame,
        "stream-1",
        "处理中…",
        False,
    )


@pytest.mark.asyncio
async def test_wecom_reply_stream_finish() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    adapter._client = AsyncMock()
    adapter._client.reply_stream = AsyncMock()

    frame = {"body": {"chatid": "chat1", "text": {"content": "hello"}}}
    event = message_event_from_frame(frame)

    await adapter.reply_stream(event, "stream-1", "done", finish=True)

    adapter._client.reply_stream.assert_awaited_once_with(
        frame,
        "stream-1",
        "done",
        True,
    )


@pytest.mark.asyncio
async def test_wecom_push_uses_send_message() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    adapter._client = AsyncMock()
    adapter._client.send_message = AsyncMock()

    await adapter.push(PushTarget(chat_id="chat1", chat_type=2), "task done")

    adapter._client.send_message.assert_awaited_once_with(
        "chat1",
        {"msgtype": "markdown", "markdown": {"content": "task done"}},
    )


@pytest.mark.asyncio
async def test_wecom_push_direct_chat() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    adapter._client = AsyncMock()
    adapter._client.send_message = AsyncMock()

    await adapter.push(PushTarget(chat_id="user1", chat_type=1), "hello")

    adapter._client.send_message.assert_awaited_once_with(
        "user1",
        {"msgtype": "markdown", "markdown": {"content": "hello"}},
    )
