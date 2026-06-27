import json

import pytest

from zero_agent.observability import (
    bind_contextvars,
    clear_contextvars,
    configure_logging,
    get_logger,
)
from zero_agent.settings import Settings


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    log = get_logger("zero_agent.test")
    log.info("test.event", platform="wecom")

    captured = capsys.readouterr()
    payload = json.loads(captured.err.strip())
    assert payload["event"] == "test.event"
    assert payload["level"] == "info"
    assert payload["logger"] == "zero_agent.test"
    assert payload["platform"] == "wecom"
    assert "ts" in payload


def test_configure_logging_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="WARNING", json=True)
    log = get_logger("zero_agent.test.level")
    log.debug("hidden")
    log.info("hidden too")
    log.warning("visible")

    captured = capsys.readouterr()
    assert "hidden" not in captured.err
    assert "visible" in captured.err


def test_configure_logging_plain_text(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=False)
    log = get_logger("zero_agent.test.plain")
    log.info("plain.message")

    captured = capsys.readouterr()
    assert "plain.message" in captured.err


def test_bind_contextvars_merged_into_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    clear_contextvars()
    bind_contextvars(session_key="wecom:chat1:user1", thread_id="wecom:chat1:user1")
    try:
        get_logger("zero_agent.test.context").info("dispatch.start")
    finally:
        clear_contextvars()

    captured = capsys.readouterr()
    payload = json.loads(captured.err.strip())
    assert payload["event"] == "dispatch.start"
    assert payload["session_key"] == "wecom:chat1:user1"
    assert payload["thread_id"] == "wecom:chat1:user1"


def test_settings_log_defaults() -> None:
    settings = Settings()
    assert settings.log_level == "INFO"
    assert settings.log_json is True
