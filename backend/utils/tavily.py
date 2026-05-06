# backend/utils/tavily.py
import os
import asyncio
from tavily import TavilyClient

def _get_client():
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY not set; set it or provide api_key")
    return TavilyClient(api_key=key)

async def generate_response(prompt: str):
    client = _get_client()
    # client.search is synchronous and returns a dict — run it in a thread
    return await asyncio.to_thread(client.search, prompt)