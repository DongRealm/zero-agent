from zero_agent.gateway.protocol import MessageEvent, MessageType, PushTarget
from zero_agent.session.models import SessionKey


def test_push_target_fields() -> None:
    target = PushTarget(chat_id="chat1", chat_type=2)
    assert target.chat_id == "chat1"
    assert target.chat_type == 2


def test_message_event_defaults() -> None:
    event = MessageEvent(platform="wecom", content="hello")

    assert event.session_id == ""
    assert event.msg_type is MessageType.TEXT
    assert event.push_target.chat_id == ""
    assert event.push_target.chat_type is None
    assert event.reply_to == {}
    assert event.extra is None


def test_message_event_with_outbound_fields() -> None:
    frame = {"body": {"chatid": "chat1", "userid": "user1"}}
    event = MessageEvent(
        platform="wecom",
        content="hello",
        session_id=SessionKey(platform="wecom", chat_id="chat1", user_id="user1").to_id(),
        msg_type=MessageType.TEXT,
        push_target=PushTarget(chat_id="chat1", chat_type=2),
        reply_to=frame,
        extra={"source": "test"},
    )

    assert event.session_id == "wecom:chat1:user1"
    assert event.push_target == PushTarget(chat_id="chat1", chat_type=2)
    assert event.reply_to is frame
    assert event.extra == {"source": "test"}


def test_message_event_session_id_round_trip() -> None:
    key = SessionKey(platform="wecom", chat_id="chat2", user_id="user2")
    event = MessageEvent(
        platform="wecom",
        content="hi",
        session_id=key.to_id(),
        push_target=PushTarget(chat_id="chat2"),
    )

    assert SessionKey.from_id(event.session_id) == key
