import json

import pytest

from zero_agent.observability import configure_logging, get_logger, message_context
from zero_agent.observability.context import bind_thread_id


def test_message_context_binds_session_key(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    session_key = "wecom:chat1:user1"

    with message_context(session_key=session_key):
        get_logger("zero_agent.test.context").info("dispatch.start")

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["event"] == "dispatch.start"
    assert payload["session_key"] == session_key
    assert "thread_id" not in payload


def test_message_context_binds_thread_id(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    session_key = "wecom:chat1:user1"
    thread_id = "wecom:chat1:user1:gen1"

    with message_context(session_key=session_key, thread_id=thread_id):
        get_logger("zero_agent.test.context").info("agent.invoke.start")

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["session_key"] == session_key
    assert payload["thread_id"] == thread_id


def test_bind_thread_id_updates_context(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)

    with message_context(session_key="wecom:chat1:user1"):
        bind_thread_id("wecom:chat1:user1:gen2")
        get_logger("zero_agent.test.context").info("agent.invoke.end")

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["session_key"] == "wecom:chat1:user1"
    assert payload["thread_id"] == "wecom:chat1:user1:gen2"


def test_message_context_clears_on_exit(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)

    with message_context(session_key="wecom:chat1:user1"):
        pass
    get_logger("zero_agent.test.context").info("after.context")

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["event"] == "after.context"
    assert "session_key" not in payload
