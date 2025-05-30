"""
Synchronous Perplexity integration for Google ADK agents
"""
import os
import json
import requests
from typing import Any, Dict
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext


def search_perplexity_sync(query: str) -> str:
    """
    Search the web using Perplexity AI for current information.
    
    Use this tool to find information about:
    - Companies and websites (e.g., "What does revsup.com offer?")
    - Current trends and news
    - Industry information
    - Any external or up-to-date information
    
    Args:
        query: The search query (e.g., "revsup.com offerings services")
        
    Returns:
        str: Search results from Perplexity
    """
    api_key = "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"
    api_url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that provides accurate, current information about companies, websites, and industry trends."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "No response from Perplexity")
            return f"Search Results:\n\n{content}"
        else:
            return f"Error: Perplexity API returned status {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error searching: {str(e)}"


class PerplexitySearchTool(BaseTool):
    """Tool for searching with Perplexity AI"""
    
    def __init__(self):
        super().__init__(
            name="perplexity_web_search",
            description="Search the web for current information about companies, websites, trends, or any external information"
        )
    
    async def run_async(self, *, args: Dict[str, Any], tool_context: ToolContext) -> Any:
        """Execute search"""
        query = args.get('query', '')
        if not query:
            return "Error: No search query provided"
        
        # Use the sync function
        return search_perplexity_sync(query)


def get_perplexity_tools_sync():
    """Get synchronous Perplexity tools for Google ADK"""
    return [
        search_perplexity_sync,  # Function-based tool
        PerplexitySearchTool()   # Class-based tool
    ]