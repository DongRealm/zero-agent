from langchain_tavily import TavilySearch

from zero_agent.settings import settings

tavily_search = TavilySearch(tavily_api_key=settings.tavily_api_key.get_secret_value(), max_results=5)
