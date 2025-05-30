#!/usr/bin/env python3
"""
Extended ADK API server with Scalar documentation
"""
import os
import sys
import subprocess
import time
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from scalar_fastapi import get_scalar_api_reference
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import json

# Start the ADK API server in a subprocess
def start_adk_server():
    env = os.environ.copy()
    process = subprocess.Popen(
        [sys.executable, "-m", "google.adk.cli", "api_server", "--port", "8001"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait for server to start
    time.sleep(3)
    return process

# Request/Response models
class MessageAgentRequest(BaseModel):
    message: str
    agent_name: Optional[str] = "revsup_candidate_qualify"
    session_id: Optional[str] = None
    user_id: Optional[str] = "default_user"

class MessageAgentResponse(BaseModel):
    response: str
    session_id: str
    agent_name: str

# Create a proxy FastAPI app
app = FastAPI(
    title="Google ADK API with Scalar Documentation",
    description="Extended API server with Scalar documentation for Google Agent Development Kit",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List available agents
@app.get("/agents", tags=["Agent Management"])
async def list_agents():
    """
    List all available agents.
    """
    try:
        response = requests.get("http://localhost:8001/list-agents")
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list agents: {response.text}"
            )
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"ADK server connection error: {str(e)}")

# Simple message-agent endpoint
@app.post("/message-agent", response_model=MessageAgentResponse, tags=["Agent Interaction"])
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
            session_url = f"http://localhost:8001/apps/{request.agent_name}/users/{request.user_id}/sessions"
            session_response = requests.post(session_url)
            
            if session_response.status_code != 200:
                raise HTTPException(
                    status_code=session_response.status_code,
                    detail=f"Failed to create session: {session_response.text}"
                )
            
            session_data = session_response.json()
            session_id = session_data.get("session_id")
        else:
            session_id = request.session_id
        
        # Send message to agent
        run_url = "http://localhost:8001/run"
        run_payload = {
            "session": {
                "app": request.agent_name,
                "user_id": request.user_id,
                "session_id": session_id
            },
            "messages": [
                {
                    "role": "user",
                    "content": request.message
                }
            ],
            "stream": False
        }
        
        run_response = requests.post(run_url, json=run_payload)
        
        if run_response.status_code != 200:
            raise HTTPException(
                status_code=run_response.status_code,
                detail=f"Failed to send message: {run_response.text}"
            )
        
        # Extract response
        response_data = run_response.json()
        agent_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
        
        return MessageAgentResponse(
            response=agent_response,
            session_id=session_id,
            agent_name=request.agent_name
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"ADK server connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# Proxy all requests to the ADK server
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy(path: str, request):
    # Get the request body
    body = await request.body()
    
    # Forward the request to the ADK server
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host header
    
    method = request.method
    url = f"http://localhost:8001/{path}"
    
    # Handle query parameters
    if request.url.query:
        url += f"?{request.url.query}"
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=body,
            stream=True,
            allow_redirects=False
        )
        
        # Return the response
        return StreamingResponse(
            response.iter_content(chunk_size=1024),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return {"error": str(e)}, 500

# Add Scalar documentation endpoint
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    # First, get the OpenAPI schema from the ADK server
    try:
        response = requests.get("http://localhost:8001/openapi.json")
        openapi_schema = response.json()
        
        # Enhance the schema with more information
        openapi_schema["info"]["title"] = "Google ADK Agent API"
        openapi_schema["info"]["description"] = """
        ## Google Agent Development Kit API
        
        This API provides endpoints for interacting with Google ADK agents.
        
        ### Key Features:
        - **Session Management**: Create and manage chat sessions
        - **Agent Interaction**: Send messages to agents and receive responses
        - **Evaluation**: Run evaluations on agent performance
        - **Artifacts**: Store and retrieve conversation artifacts
        
        ### Authentication:
        Make sure your GOOGLE_API_KEY is set in the environment or .env file.
        """
        
        # Return Scalar UI with the enhanced schema
        return get_scalar_api_reference(
            openapi_url="/openapi.json",
            title="Google ADK Agent API Documentation",
            layout="modern",
            show_sidebar=True,
            hide_download_button=False,
            hide_models=False,
            dark_mode=True,
            search_hot_key="k",
            servers=[
                {"url": "http://localhost:8000", "description": "Local development server"},
            ],
            default_open_all_tags=True,
        )
    except Exception as e:
        return {"error": f"Failed to load OpenAPI schema: {str(e)}"}, 500

# Serve the OpenAPI schema
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi():
    try:
        # Get the base schema from ADK server
        response = requests.get("http://localhost:8001/openapi.json")
        openapi_schema = response.json()
        
        # Add our custom endpoints to the schema
        if "paths" not in openapi_schema:
            openapi_schema["paths"] = {}
        
        # Add /agents endpoint
        openapi_schema["paths"]["/agents"] = {
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
                    },
                    "503": {
                        "description": "ADK server connection error"
                    }
                }
            }
        }
        
        # Add /message-agent endpoint
        openapi_schema["paths"]["/message-agent"] = {
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
                                        "agent_name": "revsup_candidate_qualify",
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
                        "description": "ADK server connection error"
                    },
                    "500": {
                        "description": "Internal server error"
                    }
                }
            }
        }
        
        # Add component schemas
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
        
        openapi_schema["components"]["schemas"]["MessageAgentRequest"] = {
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
                    "default": "revsup_candidate_qualify"
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
        
        openapi_schema["components"]["schemas"]["MessageAgentResponse"] = {
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
        
        # Update the info section
        openapi_schema["info"]["title"] = "Google ADK Agent API with Extensions"
        openapi_schema["info"]["description"] = """
        ## Google Agent Development Kit API
        
        This API provides endpoints for interacting with Google ADK agents.
        
        ### Key Features:
        - **Simplified Agent Interaction**: Use `/message-agent` for easy conversation management
        - **Session Management**: Create and manage chat sessions
        - **Agent Discovery**: List available agents with `/agents`
        - **Full ADK API**: Access all standard ADK endpoints
        - **Evaluation**: Run evaluations on agent performance
        - **Artifacts**: Store and retrieve conversation artifacts
        
        ### Quick Start:
        1. Use `/agents` to see available agents
        2. Send a message with `/message-agent` - no session setup required!
        3. Continue conversations by including the returned `session_id`
        
        ### Authentication:
        Make sure your GOOGLE_API_KEY is set in the environment or .env file.
        """
        
        return openapi_schema
    except Exception as e:
        return {"error": f"Failed to load OpenAPI schema: {str(e)}"}, 500

if __name__ == "__main__":
    # Start the ADK server
    print("Starting ADK API server on port 8001...")
    adk_process = start_adk_server()
    
    try:
        # Start the proxy server with Scalar
        print("Starting proxy server with Scalar documentation on port 8000...")
        print("Access Scalar API documentation at: http://localhost:8000/scalar")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        # Clean up
        if adk_process:
            adk_process.terminate()
            adk_process.wait()