from __future__ import annotations

from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch

from zero_agent.settings import settings

__all__ = ["build_tools"]


def build_tools() -> list[BaseTool]:
    """Return tools"""
    tools: list[BaseTool] = []
    if settings.tavily_api_key:
        tools.append(TavilySearch(tavily_api_key=settings.tavily_api_key.get_secret_value()))
    return tools
