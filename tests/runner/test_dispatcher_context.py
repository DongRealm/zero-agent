import json
from unittest.mock import AsyncMock

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr
from tests.agent.helpers import ToolFakeChatModel

from zero_agent.agent import AgentService
from zero_agent.command import CommandRouter, LangCommand, ResetCommand
from zero_agent.gateway.protocol import MessageEvent
from zero_agent.observability import configure_logging
from zero_agent.runner.dispatcher import MessageDispatcher
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry
from zero_agent.settings import Settings


@pytest.mark.asyncio
async def test_dispatcher_logs_session_and_thread_context(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(level="INFO", json=True)
    registry = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await registry.open()
    try:
        settings = Settings(
            openai_api_key=SecretStr("sk-test"),
            workspace_dir=str(tmp_path),
        )
        agent = AgentService.from_settings(
            settings,
            checkpointer=MemorySaver(),
            store=InMemoryStore(),
            model=ToolFakeChatModel(responses=["logged-reply"]),
        )
        dispatcher = MessageDispatcher(
            registry,
            CommandRouter([ResetCommand(registry), LangCommand(registry)]),
            agent,
        )
        key = SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
        event = MessageEvent(platform="wecom", content="hello", session_id=key.to_id())
        outbound = AsyncMock()
        outbound.reply = AsyncMock()

        await dispatcher.handle(event, outbound)

        lines = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.strip()]
        dispatch_end = next(item for item in lines if item.get("event") == "dispatch.end")
        agent_end = next(item for item in lines if item.get("event") == "agent.invoke.end")

        assert dispatch_end["session_key"] == key.to_id()
        assert dispatch_end["thread_id"] == await registry.resolve_thread_id(key)
        assert agent_end["session_key"] == key.to_id()
        assert agent_end["thread_id"] == dispatch_end["thread_id"]
    finally:
        await registry.close()
