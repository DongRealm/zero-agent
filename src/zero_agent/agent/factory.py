"""Construct Deep Agents LangGraph instances from application settings."""

from __future__ import annotations

from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from zero_agent.settings import Settings

_DEFAULT_SYSTEM_PROMPT = (
    "You are Zero, a personal assistant. "
    "Help the user solve problems, clarify options, and support daily planning when asked. "
    "Be concise, friendly, and practical. Reply in the user's language."
)


def build_llm(settings: Settings) -> ChatOpenAI:
    """Build the chat model from OpenAI-compatible settings."""
    kwargs: dict[str, Any] = {"model": settings.openai_model}
    if settings.openai_api_key is not None:
        kwargs["api_key"] = settings.openai_api_key.get_secret_value()
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def build_agent_graph(
    settings: Settings,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    model: BaseChatModel | None = None,
    system_prompt: str | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create a compiled Deep Agents graph with filesystem backend and checkpointer."""
    llm = model or build_llm(settings)
    backend = FilesystemBackend(root_dir=settings.workspace_dir, virtual_mode=False)
    return create_deep_agent(
        model=llm,
        backend=backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt or _DEFAULT_SYSTEM_PROMPT,
    )
