import os
import asyncio
from tavily import TavilyClient

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

class SearchService:
    @staticmethod
    async def web_search(query: str):
        # Tavily client is synchronous, run in thread
        return await asyncio.to_thread(tavily.search, query=query, search_depth="advanced")

search_service = SearchService()
