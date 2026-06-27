"""AgentService implementation."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from zero_agent.agent.factory import build_agent_graph
from zero_agent.agent.types import AgentError, AgentResult
from zero_agent.observability.context import bind_thread_id
from zero_agent.observability.setup import get_logger
from zero_agent.settings import Settings

logger = get_logger(__name__)


class AgentService:
    """Public facade for invoking the Deep Agents graph."""

    def __init__(self, graph: CompiledStateGraph[Any, Any, Any, Any]) -> None:
        self._graph = graph

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        model: BaseChatModel | None = None,
    ) -> AgentService:
        graph = build_agent_graph(settings, checkpointer=checkpointer, model=model)
        return cls(graph)

    async def invoke(self, thread_id: str, message: str) -> AgentResult:
        """Run one user turn on the given LangGraph thread."""
        bind_thread_id(thread_id)
        started = time.monotonic()
        logger.info("agent.invoke.start", content_len=len(message))
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        try:
            state = await self._graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config,
            )
        except Exception as exc:
            logger.exception("agent.invoke.error", duration_ms=_duration_ms(started))
            raise AgentError(str(exc), thread_id=thread_id) from exc

        content = _extract_assistant_content(state)
        logger.info("agent.invoke.end", duration_ms=_duration_ms(started), content_len=len(content))
        return AgentResult(content=content, thread_id=thread_id)


def _duration_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _extract_assistant_content(state: dict[str, Any]) -> str:
    messages = state.get("messages")
    if not isinstance(messages, list):
        raise AgentError("Agent returned invalid state: missing messages")

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                text_parts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                joined = "".join(text_parts).strip()
                if joined:
                    return joined

    raise AgentError("Agent returned no assistant message")
