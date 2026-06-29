"""Construct Deep Agents LangGraph instances from application settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from zero_agent.agent.tools import build_tools
from zero_agent.settings import Settings

_DEFAULT_SYSTEM_PROMPT = (
    "You are Zero, a personal assistant. "
    "Help the user solve problems, clarify options, and support daily planning when asked. "
    "Be concise, friendly, and practical. Reply in the user's language."
)


def build_llm(settings: Settings) -> BaseChatModel:
    """Build the chat model from OpenAI-compatible settings with automatic retry."""
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "max_retries": 3,
    }
    if settings.openai_api_key is not None:
        kwargs["api_key"] = settings.openai_api_key.get_secret_value()
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def _memory_namespace(_rt: object) -> tuple[str, ...]:
    return ("default",)


def load_system_prompt(settings: Settings) -> str:
    """Load system prompt from file if it exists, otherwise use default.

    Looks for `{data_dir}/SOUL.md`. If the file exists and is non-empty, its content is used as the system prompt.
    """
    prompt_file = Path(settings.resolved_data_dir) / "SOUL.md"
    if prompt_file.is_file():
        content = prompt_file.read_text(encoding="utf-8").strip()
        if content:
            return content
    return _DEFAULT_SYSTEM_PROMPT


def build_agent_graph(
    settings: Settings,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    store: BaseStore | None = None,
    model: BaseChatModel | None = None,
    system_prompt: str | None = None,
    tools: list[BaseTool] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create a compiled Deep Agents graph with long-term memory and checkpointer."""
    llm = model or build_llm(settings)
    skills_root = f"{settings.resolved_data_dir}/skills"
    Path(skills_root).mkdir(parents=True, exist_ok=True)
    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(store=store, namespace=_memory_namespace),
            "/skills/": FilesystemBackend(root_dir=skills_root, virtual_mode=True),
        },
    )
    return create_deep_agent(
        model=llm,
        memory=["/memories/AGENTS.md"],
        skills=["/skills/"],
        backend=backend,
        checkpointer=checkpointer,
        store=store,
        system_prompt=system_prompt or load_system_prompt(settings),
        tools=tools if tools is not None else build_tools(settings),
    )
