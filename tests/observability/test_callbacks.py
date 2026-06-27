import json
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.outputs import LLMResult

from zero_agent.observability import AgentLoggingCallback, configure_logging


def _parse_log_lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    err = capsys.readouterr().err.strip()
    if not err:
        return []
    return [json.loads(line) for line in err.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_llm_start_end_logs_model_and_duration(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    callback = AgentLoggingCallback()
    run_id = uuid4()

    await callback.on_chat_model_start(
        {"name": "tool-fake"},
        [[HumanMessage(content="hello there")]],
        run_id=run_id,
    )
    await callback.on_llm_end(
        LLMResult(generations=[], llm_output={"token_usage": {"total_tokens": 42}}),
        run_id=run_id,
    )

    payloads = {line["event"]: line for line in _parse_log_lines(capsys)}

    assert list(payloads) == ["llm.start", "llm.end"]
    assert payloads["llm.start"]["model"] == "tool-fake"
    assert payloads["llm.start"]["prompt_chars"] == 11
    assert payloads["llm.end"]["total_tokens"] == 42
    assert isinstance(payloads["llm.end"]["duration_ms"], int)


@pytest.mark.asyncio
async def test_tool_start_end_logs_tool_name(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    callback = AgentLoggingCallback()
    run_id = uuid4()

    await callback.on_tool_start(
        {"name": "read_file"},
        "path=/tmp/foo.py",
        run_id=run_id,
    )
    await callback.on_tool_end("file contents", run_id=run_id)

    payloads = {line["event"]: line for line in _parse_log_lines(capsys)}

    assert payloads["tool.start"]["tool_name"] == "read_file"
    assert payloads["tool.start"]["input_preview"] == "path=/tmp/foo.py"
    assert payloads["tool.end"]["output_preview"] == "file contents"
    assert isinstance(payloads["tool.end"]["duration_ms"], int)


@pytest.mark.asyncio
async def test_tool_error_logs_error_type(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", json=True)
    callback = AgentLoggingCallback()

    await callback.on_tool_error(RuntimeError("boom"), run_id=uuid4())

    payload = _parse_log_lines(capsys)[0]
    assert payload["event"] == "tool.error"
    assert payload["error_type"] == "RuntimeError"


def test_preview_truncates_long_values() -> None:
    from zero_agent.observability.callbacks import _preview

    text = "x" * 200
    assert _preview(text).endswith("…")
    assert len(_preview(text)) == 121
