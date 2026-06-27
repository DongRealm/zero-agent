"""LangChain callbacks for agent LLM and tool observability."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from zero_agent.observability.setup import get_logger

logger = get_logger(__name__)

_MAX_PREVIEW = 120


class AgentLoggingCallback(AsyncCallbackHandler):
    """Logs LLM and tool lifecycle events during Deep Agents runs."""

    def __init__(self) -> None:
        self._started: dict[UUID, float] = {}

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags, metadata, kwargs
        self._started[run_id] = time.monotonic()
        logger.info(
            "llm.start",
            model=_model_name(serialized),
            prompt_chars=_message_chars(messages),
        )

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags, kwargs
        logger.info("llm.end", duration_ms=_pop_duration_ms(self._started, run_id), **_token_usage(response))

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags, kwargs
        logger.error(
            "llm.error",
            duration_ms=_pop_duration_ms(self._started, run_id),
            error_type=type(error).__name__,
        )

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags, metadata, kwargs
        self._started[run_id] = time.monotonic()
        preview_source = input_str or inputs
        logger.info(
            "tool.start",
            tool_name=_tool_name(serialized),
            input_preview=_preview(preview_source),
        )

    async def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags, kwargs
        logger.info(
            "tool.end",
            duration_ms=_pop_duration_ms(self._started, run_id),
            output_preview=_preview(output),
        )

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        del parent_run_id, tags, kwargs
        logger.error(
            "tool.error",
            duration_ms=_pop_duration_ms(self._started, run_id),
            error_type=type(error).__name__,
        )


def _model_name(serialized: dict[str, Any]) -> str:
    name = serialized.get("name") or serialized.get("id")
    if isinstance(name, list):
        return str(name[-1]) if name else "unknown"
    if isinstance(name, str) and name:
        return name
    return "unknown"


def _tool_name(serialized: dict[str, Any]) -> str:
    name = serialized.get("name")
    if isinstance(name, str) and name:
        return name
    tool_id = serialized.get("id")
    if isinstance(tool_id, list) and tool_id:
        return str(tool_id[-1])
    return "unknown"


def _message_chars(messages: list[list[BaseMessage]]) -> int:
    total = 0
    for batch in messages:
        for msg in batch:
            content = msg.content
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if isinstance(text, str):
                            total += len(text)
    return total


def _token_usage(response: LLMResult) -> dict[str, int]:
    usage: dict[str, int] = {}
    llm_output = response.llm_output or {}
    token_usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
    if not isinstance(token_usage, dict):
        return usage
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = token_usage.get(key)
        if isinstance(value, int):
            usage[key] = value
    return usage


def _preview(value: Any, *, limit: int = _MAX_PREVIEW) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


def _pop_duration_ms(started: dict[UUID, float], run_id: UUID) -> int | None:
    started_at = started.pop(run_id, None)
    if started_at is None:
        return None
    return int((time.monotonic() - started_at) * 1000)
