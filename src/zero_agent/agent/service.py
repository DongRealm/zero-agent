"""AgentService implementation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from zero_agent.agent.factory import build_agent_graph
from zero_agent.agent.types import AgentError, AgentResult
from zero_agent.observability.callbacks import AgentLoggingCallback
from zero_agent.observability.context import bind_thread_id
from zero_agent.observability.setup import get_logger
from zero_agent.settings import Settings

logger = get_logger(__name__)

# Module-level singleton callback - stateless logger, safe to reuse cross calls
_logging_callback = AgentLoggingCallback()

# Default timeout for a single agent invocation (seconds).
_DEFAULT_TIMEOUT: float = 120.0

# Maximum graph steps before aborting (prevents tool-call loops).
_RECURSION_LIMIT: int = 30


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
        store: BaseStore | None = None,
        model: BaseChatModel | None = None,
        tools: list[BaseTool] | None = None,
    ) -> AgentService:
        graph = build_agent_graph(
            settings,
            checkpointer=checkpointer,
            store=store,
            model=model,
            tools=tools,
        )
        return cls(graph)

    async def invoke(self, thread_id: str, message: str, *, timeout: float = _DEFAULT_TIMEOUT) -> AgentResult:
        """Run one user turn on the given LangGraph thread."""
        bind_thread_id(thread_id)
        started = time.monotonic()
        logger.info("agent.invoke.start", content_len=len(message))
        config = self._build_config(thread_id)
        try:
            async with asyncio.timeout(timeout):
                state = await self._graph.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                )
        except TimeoutError as exc:
            logger.error("agent.invoke.timeout", duration_ms=_duration_ms(started))
            raise AgentError("Agent invocation timed out", thread_id=thread_id) from exc
        except AgentError:
            raise
        except Exception as exc:
            logger.exception("agent.invoke.error", duration_ms=_duration_ms(started))
            raise AgentError(str(exc), thread_id=thread_id) from exc

        content = _extract_assistant_content(state)
        logger.info("agent.invoke.end", duration_ms=_duration_ms(started), content_len=len(content))
        return AgentResult(content=content, thread_id=thread_id)

    async def stream(self, thread_id: str, message: str, *, timeout: float = _DEFAULT_TIMEOUT) -> AsyncIterator[str]:
        """Stream agent response token by token.

        Yields text chunks as they are produced by the LLM. Raises AgentError on failure or timeout.
        """
        bind_thread_id(thread_id)
        started = time.monotonic()
        logger.info("agent.stream.start", content_len=len(message))
        config = self._build_config(thread_id)
        chunk_count = 0

        try:
            async with asyncio.timeout(timeout):
                async for event in self._graph.astream_events(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                    version="v2",
                ):
                    if event["event"] == "on_chat_model_stream":
                        chunk = event["data"].get("chunk")
                        if isinstance(chunk, AIMessageChunk):
                            text = chunk.content
                            if isinstance(text, str) and text:
                                chunk_count += 1
                                yield text

        except TimeoutError as exc:
            logger.error("agent.stream.timeout", duration_ms=_duration_ms(started))
            raise AgentError("Agent stream timed out", thread_id=thread_id) from exc
        except AgentError:
            raise
        except Exception as exc:
            logger.exception("agent.stream.error", duration_ms=_duration_ms(started))
            raise AgentError(str(exc), thread_id=thread_id) from exc

        logger.info("agent.stream.end", duration_ms=_duration_ms(started), chunk_count=chunk_count)

    def _build_config(self, thread_id: str) -> RunnableConfig:
        return {
            "configurable": {"thread_id": thread_id},
            "callbacks": [AgentLoggingCallback()],
            "recursion_limit": _RECURSION_LIMIT,
        }


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
