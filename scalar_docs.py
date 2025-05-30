#!/usr/bin/env python3
"""
Scalar API documentation server for ADK API
"""
import requests
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from scalar_fastapi.scalar_fastapi import Layout, SearchHotKey
from pydantic import BaseModel
from typing import Optional
import uvicorn
import httpx
import json

# Request/Response models
class MessageAgentRequest(BaseModel):
    message: str
    agent_name: Optional[str] = "revsup-candidate-qualify"
    session_id: Optional[str] = None
    user_id: Optional[str] = "default_user"

class MessageAgentResponse(BaseModel):
    response: str
    session_id: str
    agent_name: str

app = FastAPI(
    title="ADK API Documentation",
    description="Scalar documentation for Google Agent Development Kit API"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "ADK API Documentation Server", "docs": "/scalar"}

@app.get("/test-list-apps", include_in_schema=False)
async def test_list_apps():
    """Test endpoint that calls the ADK list-apps endpoint"""
    try:
        response = requests.get("http://localhost:8000/list-apps")
        return {
            "status": "success",
            "apps": response.json(),
            "note": "This is a test endpoint. Use the Scalar UI to test the actual /list-apps endpoint."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# List available agents endpoint
@app.get("/api/agents")
async def list_agents_simple():
    """
    List all available agents.
    """
    try:
        response = requests.get("http://localhost:8000/list-agents")
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list agents: {response.text}"
            )
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"ADK server connection error: {str(e)}")

# Simple message-agent endpoint
@app.post("/api/message-agent", response_model=MessageAgentResponse)
async def message_agent(request: MessageAgentRequest):
    """
    Send a message to an agent and get a response.
    
    This endpoint simplifies agent interaction by handling session management automatically.
    If no session_id is provided, a new session will be created.
    """
    try:
        # If no session_id, create a new session
        if not request.session_id:
            # Create a new session
            session_url = f"http://localhost:8000/apps/{request.agent_name}/users/{request.user_id}/sessions"
            session_response = requests.post(session_url)
            
            if session_response.status_code != 200:
                raise HTTPException(
                    status_code=session_response.status_code,
                    detail=f"Failed to create session: {session_response.text}"
                )
            
            session_data = session_response.json()
            session_id = session_data.get("id")  # The field is 'id' not 'session_id'
            if not session_id:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get session ID from response: {session_data}"
                )
        else:
            session_id = request.session_id
        
        # Send message to agent
        run_url = "http://localhost:8000/run"
        run_payload = {
            "appName": request.agent_name,
            "userId": request.user_id,
            "sessionId": session_id,
            "newMessage": {
                "parts": [{"text": request.message}],
                "role": "user"
            }
        }
        
        run_response = requests.post(run_url, json=run_payload)
        
        if run_response.status_code != 200:
            raise HTTPException(
                status_code=run_response.status_code,
                detail=f"Failed to send message: {run_response.text}"
            )
        
        # Extract response
        response_data = run_response.json()
        
        # The response is an array with events (may include tool calls)
        agent_response = "No response"
        if isinstance(response_data, list) and len(response_data) > 0:
            # Look for the last event with text content (final response)
            for event in reversed(response_data):
                content = event.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part and part["text"]:
                        agent_response = part["text"]
                        break
                if agent_response != "No response":
                    break
        
        return MessageAgentResponse(
            response=agent_response,
            session_id=session_id,
            agent_name=request.agent_name
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"ADK server connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/api/list-agents")
async def list_agents():
    """Enhanced endpoint that returns detailed agent information including MCPs"""
    try:
        # First get the list of apps
        response = requests.get("http://localhost:8000/list-apps")
        app_names = response.json()
        
        # Load MCP configuration
        mcp_configs = {}
        try:
            with open("/root/google-agents/mcp_config.json", "r") as f:
                mcp_data = json.load(f)
                mcp_configs = mcp_data.get("mcps", {})
        except:
            pass
        
        agents = []
        for app_name in app_names:
            # Try to load the agent configuration
            agent_info = {
                "name": app_name,
                "display_name": app_name.replace("-", " ").title(),
                "status": "active",
                "mcps": []
            }
            
            # Try to import and inspect the agent
            try:
                import sys
                import importlib.util
                
                # Load the agent module
                agent_path = f"/root/google-agents/{app_name}/agent.py"
                spec = importlib.util.spec_from_file_location(f"{app_name}.agent", agent_path)
                if spec and spec.loader:
                    agent_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(agent_module)
                    
                    # Extract agent details if available
                    if hasattr(agent_module, 'root_agent'):
                        agent = agent_module.root_agent
                        if hasattr(agent, 'model'):
                            agent_info["model"] = agent.model
                        if hasattr(agent, 'instruction'):
                            agent_info["instruction"] = agent.instruction
                        if hasattr(agent, 'description'):
                            agent_info["description"] = agent.description
                        if hasattr(agent, 'name'):
                            agent_info["internal_name"] = agent.name
                        
                        # Check for MCP tools
                        if hasattr(agent, 'tools') and agent.tools:
                            for tool in agent.tools:
                                # Handle both tool objects and functions
                                if hasattr(tool, 'name'):
                                    tool_name = tool.name
                                elif hasattr(tool, '__name__'):
                                    tool_name = tool.__name__
                                else:
                                    tool_name = str(tool)
                                
                                # Check if this is a Perplexity or MCP tool
                                if 'perplexity' in tool_name.lower() or 'mcp' in tool_name.lower():
                                    # For Perplexity tools, add the MCP info
                                    if 'perplexity' in tool_name.lower():
                                        agent_info["mcps"].append({
                                            "name": "perplexity-ask",
                                            "description": mcp_configs.get("perplexity-ask", {}).get("description", "Perplexity AI search and question answering"),
                                            "tool_name": tool_name,
                                            "tool_type": "integrated"
                                        })
                                    else:
                                        # For other MCP tools
                                        for mcp_name, mcp_config in mcp_configs.items():
                                            if mcp_name in tool_name:
                                                agent_info["mcps"].append({
                                                    "name": mcp_name,
                                                    "description": mcp_config.get("description", "MCP server"),
                                                    "command": mcp_config.get("command", ""),
                                                    "tool_name": tool_name
                                                })
                            
                            # Remove duplicates based on MCP name
                            seen = set()
                            unique_mcps = []
                            for mcp in agent_info["mcps"]:
                                if mcp["name"] not in seen:
                                    seen.add(mcp["name"])
                                    unique_mcps.append(mcp)
                            agent_info["mcps"] = unique_mcps
            except Exception as e:
                agent_info["error"] = f"Could not load agent details: {str(e)}"
            
            agents.append(agent_info)
        
        return {
            "agents": agents,
            "total": len(agents)
        }
    except Exception as e:
        return JSONResponse(
            {"error": str(e)}, 
            status_code=500
        )

@app.get("/openapi-proxy.json", include_in_schema=False)
async def openapi_proxy():
    """Proxy OpenAPI spec from ADK server to avoid CORS issues"""
    try:
        response = requests.get("http://localhost:8000/openapi.json")
        spec = response.json()
        
        # Enhance the OpenAPI spec with better descriptions
        spec["info"]["title"] = "Google ADK Agent API"
        spec["info"]["description"] = """
        ## Google Agent Development Kit API
        
        This API provides endpoints for interacting with Google ADK agents.
        
        ### Quick Start:
        1. Use **GET /agents** to see available agents
        2. Send a message with **POST /message-agent** - no session setup required!
        3. Continue conversations by including the returned `session_id`
        
        ### Key Endpoints:
        
        #### Simplified Endpoints (Recommended):
        - **GET /agents** - List available agents
        - **POST /message-agent** - Send a message to an agent (handles sessions automatically)
        
        #### Standard ADK Endpoints:
        - **GET /list-agents** - List all available agents with detailed information
        - **POST /apps/{app_name}/users/{user_id}/sessions** - Create a new chat session
        - **POST /run** - Send a message to an agent
        
        ### Authentication:
        Make sure your GOOGLE_API_KEY is set in the environment or .env file.
        """
        
        # Add our custom /list-agents endpoint to the spec
        spec["paths"]["/list-agents"] = {
            "get": {
                "summary": "List Available Agents with Details",
                "description": """
                Returns a detailed list of all available agents in the system with their configurations.
                
                This endpoint provides comprehensive information about each agent including:
                - Agent name and display name
                - Model being used
                - System instructions
                - Description
                - Current status
                
                Example response:
                ```json
                {
                    "agents": [
                        {
                            "name": "revsup-candidate-qualify",
                            "display_name": "Revsup Candidate Qualify",
                            "status": "active",
                            "model": "gemini-1.5-flash",
                            "instruction": "You are a helpful AI assistant...",
                            "description": "AI assistant for qualifying revenue support candidates",
                            "internal_name": "revsup_candidate_qualify"
                        }
                    ],
                    "total": 1
                }
                ```
                """,
                "tags": ["Agent Management"],
                "responses": {
                    "200": {
                        "description": "Successful response with agent details",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "agents": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "display_name": {"type": "string"},
                                                    "status": {"type": "string"},
                                                    "model": {"type": "string"},
                                                    "instruction": {"type": "string"},
                                                    "description": {"type": "string"},
                                                    "internal_name": {"type": "string"}
                                                }
                                            }
                                        },
                                        "total": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Add /agents endpoint
        spec["paths"]["/agents"] = {
            "get": {
                "tags": ["Agent Management"],
                "summary": "List available agents",
                "description": "Returns a list of all available agents in the system.",
                "responses": {
                    "200": {
                        "description": "List of agents",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "agents": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "display_name": {"type": "string"},
                                                    "status": {"type": "string"},
                                                    "model": {"type": "string"},
                                                    "description": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Add /message-agent endpoint
        spec["paths"]["/message-agent"] = {
            "post": {
                "tags": ["Agent Interaction"],
                "summary": "Send a message to an agent",
                "description": "Send a message to an agent and get a response. This endpoint simplifies agent interaction by handling session management automatically. If no session_id is provided, a new session will be created.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/MessageAgentRequest"
                            },
                            "examples": {
                                "new_conversation": {
                                    "summary": "Start new conversation",
                                    "value": {
                                        "message": "What qualifications should a revenue support candidate have?"
                                    }
                                },
                                "continue_conversation": {
                                    "summary": "Continue existing conversation",
                                    "value": {
                                        "message": "Tell me more about technical skills",
                                        "session_id": "existing-session-id"
                                    }
                                },
                                "custom_agent": {
                                    "summary": "Message specific agent",
                                    "value": {
                                        "message": "Hello, how can you help me?",
                                        "agent_name": "revsup-candidate-qualify",
                                        "user_id": "custom-user-123"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Agent response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/MessageAgentResponse"
                                },
                                "example": {
                                    "response": "A revenue support candidate should have strong analytical skills, experience with CRM systems, and excellent communication abilities...",
                                    "session_id": "sess_12345",
                                    "agent_name": "revsup_candidate_qualify"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request"
                    },
                    "503": {
                        "description": "Service unavailable - ADK server connection error"
                    },
                    "500": {
                        "description": "Internal server error"
                    }
                }
            }
        }
        
        # Add component schemas
        if "components" not in spec:
            spec["components"] = {}
        if "schemas" not in spec["components"]:
            spec["components"]["schemas"] = {}
        
        spec["components"]["schemas"]["MessageAgentRequest"] = {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to the agent"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent to use",
                    "default": "revsup-candidate-qualify"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID to continue an existing conversation",
                    "nullable": True
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier",
                    "default": "default_user"
                }
            }
        }
        
        spec["components"]["schemas"]["MessageAgentResponse"] = {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "The agent's response"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for continuing the conversation"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent that responded"
                }
            }
        }
        
        # Mark the old /list-apps endpoint as deprecated
        if "/list-apps" in spec["paths"]:
            spec["paths"]["/list-apps"]["get"]["summary"] = "[DEPRECATED] List Available Agent Applications"
            spec["paths"]["/list-apps"]["get"]["description"] = """
            **DEPRECATED: Use /list-agents instead for detailed agent information**
            
            Returns a simple list of all available agent application names.
            
            Example response:
            ```json
            ["revsup-candidate-qualify"]
            ```
            """
            spec["paths"]["/list-apps"]["get"]["tags"] = ["Agent Management"]
            spec["paths"]["/list-apps"]["get"]["deprecated"] = True
        
        return spec
    except Exception as e:
        return {"error": str(e)}

@app.get("/scalar", include_in_schema=False) 
async def scalar_html():
    """Serve Scalar documentation UI"""
    return get_scalar_api_reference(
        openapi_url="/openapi-proxy.json",
        title="Google ADK Agent API",
        layout=Layout.MODERN,
        show_sidebar=True,
        hide_download_button=False,
        hide_models=False,
        dark_mode=True,
        search_hot_key=SearchHotKey.K,
        servers=[
            {"url": "http://5.161.60.251:8080/api", "description": "Scalar Proxy (Use this for browser testing)"},
            {"url": "http://5.161.60.251:8000", "description": "Direct ADK API Server"},
        ],
        default_open_all_tags=False,
    )

# Add a catch-all proxy for API requests to handle CORS
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_api(path: str, request: Request):
    """Proxy API requests to ADK server with CORS handling"""
    # Build the target URL
    target_url = f"http://localhost:8000/{path}"
    
    # Get query parameters
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    # Create headers, removing host
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # Get request body
    body = await request.body()
    
    # Make the request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                timeout=30.0
            )
            
            # Return response with CORS headers
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        except Exception as e:
            return JSONResponse(
                {"error": str(e)}, 
                status_code=500,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
                    "Access-Control-Allow-Headers": "*"
                }
            )

if __name__ == "__main__":
    print("Starting Scalar documentation server on port 8080...")
    print("Access documentation at: http://localhost:8080/scalar")
    print("Make sure ADK API server is running on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8080)