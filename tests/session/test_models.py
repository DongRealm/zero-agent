from datetime import UTC, datetime

import pytest

from zero_agent.gateway.protocol import MessageEvent
from zero_agent.session.models import SessionKey, SessionRecord


def test_session_key_to_id_group_chat() -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    assert key.to_id() == "wecom:chat1:user1"


def test_session_key_to_id_direct_message() -> None:
    key = SessionKey(platform="wecom", chat_id="chat2")
    assert key.to_id() == "wecom:chat2"


def test_session_key_to_id_unknown() -> None:
    key = SessionKey(platform="wecom", chat_id="")
    assert key.to_id() == "wecom:unknown"


@pytest.mark.parametrize(
    ("session_id", "key"),
    [
        ("wecom:chat1:user1", SessionKey(platform="wecom", chat_id="chat1", user_id="user1")),
        ("wecom:chat2", SessionKey(platform="wecom", chat_id="chat2")),
        ("wecom:unknown", SessionKey(platform="wecom", chat_id="")),
    ],
)
def test_session_key_from_id_round_trip(session_id: str, key: SessionKey) -> None:
    assert SessionKey.from_id(session_id) == key
    assert key.to_id() == session_id


def test_session_key_from_event() -> None:
    event = MessageEvent(
        platform="wecom",
        content="hi",
        session_id="wecom:chat1:user1",
    )
    assert SessionKey.from_event(event) == SessionKey(
        platform="wecom",
        chat_id="chat1",
        user_id="user1",
    )


def test_session_key_from_event_without_session_id() -> None:
    event = MessageEvent(platform="wecom", content="hi")
    assert SessionKey.from_event(event) == SessionKey(platform="wecom", chat_id="")


def test_session_record_touch() -> None:
    key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
    record = SessionRecord(key=key, thread_id=key.to_id())
    updated = record.touch(at=datetime(2026, 1, 1, tzinfo=UTC))
    assert updated.last_active_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert updated.session_id == "wecom:chat1:user1"
