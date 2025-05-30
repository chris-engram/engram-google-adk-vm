#!/usr/bin/env python3
"""
Scalar API documentation server for ADK API
"""
import requests
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from scalar_fastapi.scalar_fastapi import Layout, SearchHotKey
import uvicorn
import httpx

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

@app.get("/api/list-agents")
async def list_agents():
    """Enhanced endpoint that returns detailed agent information"""
    try:
        # First get the list of apps
        response = requests.get("http://localhost:8000/list-apps")
        app_names = response.json()
        
        agents = []
        for app_name in app_names:
            # Try to load the agent configuration
            agent_info = {
                "name": app_name,
                "display_name": app_name.replace("-", " ").title(),
                "status": "active"
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
        1. Click on any endpoint below to expand it
        2. Click "Try it out" button
        3. Fill in any required parameters
        4. Click "Execute" to test the endpoint
        
        ### Key Endpoints:
        - **GET /list-agents** - List all available agents with detailed information
        - **POST /apps/{app_name}/users/{user_id}/sessions** - Create a new chat session
        - **POST /run** - Send a message to an agent
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