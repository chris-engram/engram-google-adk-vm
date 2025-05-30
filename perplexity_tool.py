"""
Direct Perplexity API integration for Google ADK agents
"""
import os
import json
import aiohttp
from typing import Any, Dict
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext


class PerplexitySearchTool(BaseTool):
    """Tool for searching with Perplexity AI"""
    
    def __init__(self):
        super().__init__(
            name="perplexity_web_search",
            description="Search the web for current information about companies, websites, trends, or any external information"
        )
        # Get API key from config
        self.api_key = self._get_api_key()
        self.api_url = "https://api.perplexity.ai/chat/completions"
    
    def _get_api_key(self) -> str:
        """Get Perplexity API key from config"""
        try:
            with open("/root/google-agents/mcp_config.json", 'r') as f:
                config = json.load(f)
                return config.get('mcps', {}).get('perplexity-ask', {}).get('env', {}).get('PERPLEXITY_API_KEY', '')
        except:
            # Fallback to environment variable
            return os.getenv('PERPLEXITY_API_KEY', '')
    
    async def run_async(self, *, args: Dict[str, Any], tool_context: ToolContext) -> Any:
        """Execute search"""
        query = args.get('query', '')
        if not query:
            return "Error: No search query provided"
        
        if not self.api_key:
            return "Error: No Perplexity API key configured"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "No response from Perplexity")
                        return f"Search Results:\n\n{content}"
                    else:
                        error_text = await response.text()
                        return f"Error: Perplexity API returned status {response.status}: {error_text}"
        except Exception as e:
            return f"Error searching: {str(e)}"


async def search_perplexity(query: str) -> str:
    """Function-based tool for Perplexity search
    
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
    tool = PerplexitySearchTool()
    from google.adk.tools.tool_context import ToolContext
    context = ToolContext()
    result = await tool.run_async(args={'query': query}, tool_context=context)
    return result


def get_perplexity_tools():
    """Get Perplexity tools for Google ADK"""
    return [
        search_perplexity,  # Function-based tool
        PerplexitySearchTool()  # Class-based tool
    ]