import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from pydantic import SecretStr
from tests.agent.helpers import ToolFakeChatModel

from zero_agent.agent import AgentResult, AgentService
from zero_agent.agent.types import AgentError
from zero_agent.observability import configure_logging
from zero_agent.settings import Settings


def _parse_log_lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    err = capsys.readouterr().err.strip()
    if not err:
        return []
    return [json.loads(line) for line in err.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_invoke_emits_llm_callback_logs(capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    configure_logging(level="INFO", json=True)
    settings = Settings(openai_api_key=SecretStr("sk-test"), workspace_dir=str(tmp_path))
    service = AgentService.from_settings(
        settings,
        checkpointer=MemorySaver(),
        model=ToolFakeChatModel(responses=["hello back"]),
    )

    await service.invoke("thread-callback", "hello")

    events = [line["event"] for line in _parse_log_lines(capsys)]
    assert "llm.start" in events
    assert "llm.end" in events
    assert "agent.invoke.start" in events
    assert "agent.invoke.end" in events


@pytest.fixture
def agent_service(tmp_path) -> AgentService:
    settings = Settings(
        openai_api_key=SecretStr("sk-test"),
        workspace_dir=str(tmp_path),
    )
    model = ToolFakeChatModel(responses=["first-reply", "second-reply"])
    return AgentService.from_settings(
        settings,
        checkpointer=MemorySaver(),
        model=model,
    )


@pytest.mark.asyncio
async def test_invoke_returns_agent_result(agent_service: AgentService) -> None:
    result = await agent_service.invoke("thread-1", "hello")

    assert isinstance(result, AgentResult)
    assert result.thread_id == "thread-1"
    assert result.content == "first-reply"


@pytest.mark.asyncio
async def test_invoke_multi_turn_same_thread(agent_service: AgentService) -> None:
    first = await agent_service.invoke("thread-1", "hello")
    second = await agent_service.invoke("thread-1", "follow up")

    assert first.content == "first-reply"
    assert second.content == "second-reply"


@pytest.mark.asyncio
async def test_invoke_returns_thread_id(agent_service: AgentService) -> None:
    result = await agent_service.invoke("my-thread", "hello")
    assert result.thread_id == "my-thread"


@pytest.mark.asyncio
async def test_invoke_wraps_graph_errors(tmp_path) -> None:
    settings = Settings(openai_api_key=SecretStr("sk-test"), workspace_dir=str(tmp_path))

    class BrokenModel(ToolFakeChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("boom")

    service = AgentService.from_settings(
        settings,
        checkpointer=MemorySaver(),
        model=BrokenModel(responses=["x"]),
    )

    with pytest.raises(AgentError, match="boom") as exc_info:
        await service.invoke("thread-x", "hello")

    assert exc_info.value.thread_id == "thread-x"
