"""End-to-end pipeline: gateway message → dispatcher → agent reply."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr
from tests.agent.helpers import ToolFakeChatModel

from zero_agent.agent import AgentService
from zero_agent.command import CommandRouter, LangCommand, ResetCommand
from zero_agent.gateway.platforms.wecom import WecomAdapter, message_event_from_frame
from zero_agent.runner.app import wire_gate_runner
from zero_agent.session.models import SessionKey
from zero_agent.session.registry import SessionRegistry
from zero_agent.settings import Settings


@pytest.fixture
def pipeline_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=str(tmp_path),
        workspace_dir=str(tmp_path / "workspace"),
        openai_api_key=SecretStr("sk-test"),
        wecom_bot_id="bot-1",
        wecom_bot_secret=SecretStr("secret"),
    )


@pytest.mark.asyncio
async def test_wecom_message_to_agent_reply(pipeline_settings: Settings, tmp_path: Path) -> None:
    registry = SessionRegistry(
        str(tmp_path / "session.db"),
        default_locale="zh",
        checkpoint_db_path=str(tmp_path / "checkpoints.db"),
    )
    await registry.open()
    try:
        agent = AgentService.from_settings(
            pipeline_settings,
            checkpointer=MemorySaver(),
            store=InMemoryStore(),
            model=ToolFakeChatModel(responses=["pipeline-reply"]),
        )
        commands = CommandRouter(
            [
                ResetCommand(registry),
                LangCommand(registry),
            ]
        )
        adapter = WecomAdapter(
            bot_id=pipeline_settings.wecom_bot_id or "",
            secret=pipeline_settings.wecom_bot_secret,
        )
        adapter._client = AsyncMock()
        adapter._client.reply = AsyncMock()
        adapter._client.reply_stream = AsyncMock()

        runner = wire_gate_runner(registry, commands, agent, {"wecom": adapter})

        frame = {
            "body": {
                "chatid": "chat1",
                "chattype": 2,
                "userid": "user1",
                "text": {"content": "hello agent"},
            }
        }
        event = message_event_from_frame(frame)
        await adapter.handle_message(event)
        await asyncio.sleep(0.05)

        thread_id = await registry.resolve_thread_id(
            SessionKey(platform="wecom", chat_id="chat1", user_id="user1")
        )
        assert adapter._client.reply_stream.await_count == 2
        adapter._client.reply_stream.assert_any_await(
            frame,
            thread_id,
            "处理中…",
            False,
        )
        adapter._client.reply_stream.assert_awaited_with(
            frame,
            thread_id,
            "pipeline-reply",
            True,
        )
        adapter._client.reply.assert_not_awaited()
        assert runner.adapters["wecom"] is adapter
    finally:
        await registry.close()


@pytest.mark.asyncio
async def test_wecom_reset_command_through_pipeline(
    pipeline_settings: Settings,
    tmp_path: Path,
) -> None:
    registry = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await registry.open()
    try:
        agent = AgentService.from_settings(
            pipeline_settings,
            checkpointer=MemorySaver(),
            store=InMemoryStore(),
            model=ToolFakeChatModel(responses=["unused"]),
        )
        commands = CommandRouter(
            [
                ResetCommand(registry),
                LangCommand(registry),
            ]
        )
        adapter = WecomAdapter(
            bot_id=pipeline_settings.wecom_bot_id or "",
            secret=pipeline_settings.wecom_bot_secret,
        )
        adapter._client = AsyncMock()
        adapter._client.reply = AsyncMock()

        wire_gate_runner(registry, commands, agent, {"wecom": adapter})

        frame = {
            "body": {
                "chatid": "chat1",
                "userid": "user1",
                "text": {"content": "/reset"},
            }
        }
        await adapter.handle_message(message_event_from_frame(frame))
        await asyncio.sleep(0.05)

        reply_body = adapter._client.reply.await_args.args[1]
        assert reply_body["markdown"]["content"] == "已开启新对话，上下文已清空。"
    finally:
        await registry.close()


@pytest.mark.asyncio
async def test_wecom_lang_command_through_pipeline(
    pipeline_settings: Settings,
    tmp_path: Path,
) -> None:
    registry = SessionRegistry(str(tmp_path / "session.db"), default_locale="zh")
    await registry.open()
    try:
        agent = AgentService.from_settings(
            pipeline_settings,
            checkpointer=MemorySaver(),
            store=InMemoryStore(),
            model=ToolFakeChatModel(responses=["unused"]),
        )
        commands = CommandRouter(
            [
                ResetCommand(registry),
                LangCommand(registry),
            ]
        )
        adapter = WecomAdapter(
            bot_id=pipeline_settings.wecom_bot_id or "",
            secret=pipeline_settings.wecom_bot_secret,
        )
        adapter._client = AsyncMock()
        adapter._client.reply = AsyncMock()

        wire_gate_runner(registry, commands, agent, {"wecom": adapter})

        frame = {
            "body": {
                "chatid": "chat1",
                "userid": "user1",
                "text": {"content": "/lang en"},
            }
        }
        await adapter.handle_message(message_event_from_frame(frame))
        await asyncio.sleep(0.05)

        reply_body = adapter._client.reply.await_args.args[1]
        assert reply_body["markdown"]["content"] == "Language switched to English."
    finally:
        await registry.close()
