#!/usr/bin/env python3
"""
Extended ADK API server with Scalar documentation
"""
import os
import sys
import subprocess
import time
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from scalar_fastapi import get_scalar_api_reference
import uvicorn

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
        response = requests.get("http://localhost:8001/openapi.json")
        return response.json()
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