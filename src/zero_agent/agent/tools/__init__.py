from langchain.tools import BaseTool

from zero_agent.agent.tools.web_search import tavily_search

__all__ = ["all_tools"]

all_tools: list[BaseTool] = [tavily_search]
