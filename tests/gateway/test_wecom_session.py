from zero_agent.gateway.platforms.wecom import parse_wecom_session_id


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


def test_parse_wecom_session_id_unknown() -> None:
    assert parse_wecom_session_id({}) == "wecom:unknown"
