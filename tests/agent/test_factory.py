import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr

from zero_agent.agent.factory import build_agent_graph, build_llm
from zero_agent.agent.types import AgentError, AgentResult
from zero_agent.settings import Settings


def test_agent_result_fields() -> None:
    result = AgentResult(content="hello", thread_id="t1")
    assert result.content == "hello"
    assert result.thread_id == "t1"


def test_agent_error_carries_thread_id() -> None:
    err = AgentError("failed", thread_id="t2")
    assert str(err) == "failed"
    assert err.thread_id == "t2"


def test_build_llm_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    settings = Settings(
        openai_api_key=SecretStr("sk-test"),
        openai_base_url="https://example.com/v1",
        openai_model="gpt-4o-mini",
    )
    llm = build_llm(settings)
    assert llm.model_name == "gpt-4o-mini"
    assert llm.openai_api_key.get_secret_value() == "sk-test"
    assert llm.openai_api_base == "https://example.com/v1"


def test_build_agent_graph_with_memory_saver(tmp_path) -> None:
    settings = Settings(
        openai_api_key=SecretStr("sk-test"),
        workspace_dir=str(tmp_path),
    )
    fake_model = FakeListChatModel(responses=["ok"])

    graph = build_agent_graph(
        settings,
        checkpointer=MemorySaver(),
        store=InMemoryStore(),
        model=fake_model,
    )

    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")
