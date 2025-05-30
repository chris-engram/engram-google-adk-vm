"""
MCP (Model Context Protocol) integration for Google ADK agents - Version 2
Direct integration approach for better compatibility
"""
import os
import json
import subprocess
from typing import Any, Dict, List, Optional
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
import asyncio


class MCPTool(BaseTool):
    """Tool for interacting with MCP servers"""
    
    def __init__(self, config_path: str = None):
        super().__init__(
            name="mcp_query",
            description="Query an MCP (Model Context Protocol) server for information"
        )
        if config_path is None:
            config_path = "/root/google-agents/mcp_config.json"
        self.config_path = config_path
        self.mcp_configs = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get('mcps', {})
        except Exception as e:
            print(f"Error loading MCP config: {e}")
            return {}
    
    async def run_async(self, *, args: Dict[str, Any], tool_context: ToolContext) -> Any:
        """Execute MCP query"""
        query = args.get('query', '')
        mcp_name = args.get('mcp_name', 'perplexity-ask')
        
        if mcp_name not in self.mcp_configs:
            return {"error": f"MCP '{mcp_name}' not configured"}
        
        config = self.mcp_configs[mcp_name]
        
        # Build the command
        cmd = [config['command']] + config['args']
        
        # Set up environment
        env = {**os.environ, **config.get('env', {})}
        
        # Create the MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "perplexity_ask",
                "arguments": {
                    "messages": [
                        {
                            "role": "user",
                            "content": query
                        }
                    ]
                }
            },
            "id": 1
        }
        
        try:
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Send request and get response
            stdout, stderr = await process.communicate(
                input=json.dumps(mcp_request).encode()
            )
            
            if stderr:
                print(f"MCP stderr: {stderr.decode()}")
            
            # Parse response
            response = json.loads(stdout.decode())
            
            if "error" in response:
                return {"error": response["error"]}
            
            # Extract the actual content from the MCP response
            result = response.get("result", {})
            content = result.get("content", [])
            
            if content and isinstance(content, list) and len(content) > 0:
                return content[0].get("text", "No response from MCP")
            else:
                return "No response from MCP"
                
        except Exception as e:
            return f"MCP execution error: {str(e)}"


class PerplexitySearchTool(BaseTool):
    """Tool specifically for Perplexity web searches"""
    
    def __init__(self):
        super().__init__(
            name="perplexity_web_search",
            description="Search the web using Perplexity AI for current information about companies, websites, trends, or any external information"
        )
        self.mcp_tool = MCPTool()
    
    async def run_async(self, *, args: Dict[str, Any], tool_context: ToolContext) -> Any:
        """Execute search"""
        query = args.get('query', '')
        if not query:
            return "Error: No search query provided"
        
        # Call the MCP tool with perplexity-ask
        result = await self.mcp_tool.run_async(
            args={'query': query, 'mcp_name': 'perplexity-ask'},
            tool_context=tool_context
        )
        
        return result


def perplexity_search(query: str) -> str:
    """Function-based tool for searching with Perplexity
    
    Args:
        query: The search query
        
    Returns:
        str: Search results from Perplexity
    """
    # This is a simplified sync wrapper - in production you'd want proper async handling
    import asyncio
    
    async def _search():
        tool = PerplexitySearchTool()
        # Create a minimal tool context
        from google.adk.tools.tool_context import ToolContext
        context = ToolContext()
        return await tool.run_async(args={'query': query}, tool_context=context)
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_search())


def get_mcp_tools_v2() -> List:
    """Get all configured MCP tools"""
    return [
        perplexity_search,  # Function-based tool
        PerplexitySearchTool()  # Class-based tool for more control
    ]