"""
MCP (Model Context Protocol) integration for Google ADK agents
"""
import subprocess
import json
import asyncio
from typing import Any, Dict, List, Optional
from google.adk.tools import BaseTool
from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """Request model for MCP tool"""
    query: str = Field(description="The query to send to the MCP server")
    mcp_name: str = Field(default="perplexity-ask", description="Name of the MCP to use")


class MCPTool(BaseTool):
    """Tool for interacting with MCP servers"""
    
    def __init__(self, config_path: str = None):
        super().__init__(
            name="mcp_query",
            description="Query an MCP (Model Context Protocol) server for information"
        )
        self.input_schema = MCPRequest
        if config_path is None:
            # Use absolute path
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
    
    async def run(self, query: str, mcp_name: str = "perplexity-ask") -> Dict[str, Any]:
        """Execute MCP query"""
        if mcp_name not in self.mcp_configs:
            return {"error": f"MCP '{mcp_name}' not configured"}
        
        config = self.mcp_configs[mcp_name]
        
        # Build the command
        cmd = [config['command']] + config['args']
        
        # Set up environment
        env = {**subprocess.os.environ, **config.get('env', {})}
        
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
                return {"response": content[0].get("text", "No response from MCP")}
            else:
                return {"response": "No response from MCP"}
                
        except Exception as e:
            return {"error": f"MCP execution error: {str(e)}"}


class PerplexityTool(BaseTool):
    """Simplified tool specifically for Perplexity searches"""
    
    def __init__(self):
        super().__init__(
            name="perplexity_search",
            description="Search the web using Perplexity AI for up-to-date information"
        )
        self.mcp_tool = MCPTool()
    
    async def run(self, query: str) -> str:
        """Execute Perplexity search"""
        result = await self.mcp_tool.run(query=query, mcp_name="perplexity-ask")
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        return result.get("response", "No results found")


def get_mcp_tools() -> List[BaseTool]:
    """Get all configured MCP tools"""
    return [
        MCPTool(),
        PerplexityTool()
    ]