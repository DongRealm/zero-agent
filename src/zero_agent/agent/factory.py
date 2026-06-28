"""Construct Deep Agents LangGraph instances from application settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from zero_agent.agent.context import AgentContext
from zero_agent.agent.tools import all_tools
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


def _memory_namespace(rt: object) -> tuple[str, ...]:
    """Resolve the LangGraph Store namespace for long-term memory (``/memories/``).

    ``StoreBackend`` calls this on each read/write. The returned tuple becomes
    the store ``prefix`` (e.g. the WeCom ``user_id``), so each user gets an
    isolated ``/memories/AGENTS.md`` under ``.local/store.db``.

    Requires ``context_schema=AgentContext`` and ``context=AgentContext(user_id=...)``
    on each invoke (see ``AgentService.invoke``).

    Personal-only agent (single user, shared memory bucket):

    Replace this function with a fixed namespace, e.g.
    ``namespace=lambda rt: ("zero",)``, and remove ``context_schema`` /
    ``AgentContext`` if nothing else needs runtime context. Migrate existing
    store rows if the prefix changes (e.g. from a per-user id to ``"zero"``).
    """
    context = getattr(rt, "context", None)
    user_id = getattr(context, "user_id", None)
    if isinstance(user_id, str) and user_id:
        return (user_id,)
    return ("default",)


def build_agent_graph(
    settings: Settings,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    store: BaseStore | None = None,
    model: BaseChatModel | None = None,
    system_prompt: str | None = None,
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
        context_schema=AgentContext,
        backend=backend,
        checkpointer=checkpointer,
        store=store,
        system_prompt=system_prompt or _DEFAULT_SYSTEM_PROMPT,
        tools=all_tools,
    )
