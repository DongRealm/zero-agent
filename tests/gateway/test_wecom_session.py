from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from zero_agent.gateway.platforms.wecom import (
    WecomAdapter,
    message_event_from_frame,
    parse_wecom_push_target,
    parse_wecom_session_id,
    wecom_session_key_from_frame,
)
from zero_agent.gateway.protocol import PushTarget
from zero_agent.session.models import SessionKey


def test_parse_wecom_session_id_group_chat() -> None:
    frame = {
        "body": {
            "chatid": "chat1",
            "userid": "user1",
            "text": {"content": "hello"},
        }
    }
    assert parse_wecom_session_id(frame) == "wecom:chat1:user1"


def test_parse_wecom_session_id_direct_message() -> None:
    frame = {"body": {"chatid": "chat2", "text": {"content": "hi"}}}
    assert parse_wecom_session_id(frame) == "wecom:chat2"


def test_parse_wecom_session_id_aibot_flat_frame() -> None:
    frame = {
        "chattype": "single",
        "from": {"userid": "ZhangYiDong"},
        "msgtype": "text",
        "text": {"content": "hello"},
    }
    assert parse_wecom_session_id(frame) == "wecom:ZhangYiDong:ZhangYiDong"


def test_message_event_from_aibot_flat_frame() -> None:
    frame = {
        "msgid": "msg-2",
        "chattype": "single",
        "from": {"userid": "ZhangYiDong"},
        "text": {"content": "我喜欢甜食"},
    }
    event = message_event_from_frame(frame)

    assert event.content == "我喜欢甜食"
    assert event.session_id == "wecom:ZhangYiDong:ZhangYiDong"
    assert event.push_target.chat_id == "ZhangYiDong"


def test_parse_wecom_session_id_unknown() -> None:
    assert parse_wecom_session_id({}) == "wecom:unknown"


def test_parse_wecom_push_target_group_chat() -> None:
    frame = {
        "body": {
            "chatid": "chat1",
            "chattype": 2,
            "userid": "user1",
        }
    }
    assert parse_wecom_push_target(frame) == PushTarget(chat_id="chat1", chat_type=2)


def test_parse_wecom_push_target_direct_message() -> None:
    frame = {"body": {"chatid": "chat2", "chat_type": 1}}
    assert parse_wecom_push_target(frame) == PushTarget(chat_id="chat2", chat_type=1)


def test_message_event_from_frame_sets_outbound_fields() -> None:
    frame = {
        "msgid": "msg-1",
        "body": {
            "chatid": "chat1",
            "chattype": 2,
            "userid": "user1",
            "text": {"content": "hello"},
        },
    }
    event = message_event_from_frame(frame)

    assert event.platform == "wecom"
    assert event.content == "hello"
    assert event.session_id == SessionKey(platform="wecom", chat_id="chat1", user_id="user1").to_id()
    assert event.push_target == PushTarget(chat_id="chat1", chat_type=2)
    assert event.reply_to is frame
    assert event.extra is frame
    assert SessionKey.from_id(event.session_id) == wecom_session_key_from_frame(frame)


@pytest.mark.asyncio
async def test_send_reply_uses_reply_to() -> None:
    adapter = WecomAdapter(bot_id="bot", secret=SecretStr("secret"))
    adapter._client = AsyncMock()
    adapter._client.reply = AsyncMock()

    frame = {"body": {"chatid": "chat1", "text": {"content": "hello"}}}
    event = message_event_from_frame(frame)
    event.extra = {"legacy": True}

    await adapter._send_reply(event, "pong")

    adapter._client.reply.assert_awaited_once_with(
        frame,
        {"msgtype": "markdown", "markdown": {"content": "pong"}},
    )
