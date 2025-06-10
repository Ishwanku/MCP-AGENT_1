"""
Server Utilities for MCP Document Merge Agent

This module provides utility functions and setup for the MCP Agent server.
It includes functionality for starting the server, handling server configuration,
and other server-related tasks that support the main FastAPI application in
`document_merge_agent.py`.

Key Features:
- Provides server startup logic and configuration.
- Supports the main FastAPI application with necessary utilities.
- Ensures proper initialization of server components.

Usage:
    This module is typically used internally by the MCP Agent system.
    It is invoked as part of the server startup process via `run.py` or directly
    when running the agent module.

FastAPI-based MCP server implementation.

This module provides a FastAPI-based server implementation for the MCP (Multi-Component Protocol)
agent system. It handles tool registration, execution, and API key authentication.

Key Features:
- FastAPI-based REST API for tool execution.
- Tool registration and management for extensibility.
- API key authentication for secure access.
- Health check endpoint for monitoring.
- Detailed error handling for robust operation.
- Request validation using Pydantic models.

Example:
    ```python
    server = FastMCP("DemoAgent", port=8000, api_key="secret-key")
    server.register_tool("echo", echo_tool)
    server.run()
    ```

Dependencies:
    - fastapi: For the web server.
    - uvicorn: For ASGI server.
    - pydantic: For request/response models.
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from typing import Dict, Any, Callable, Optional
import uvicorn
from pydantic import BaseModel

class ToolRequest(BaseModel):
    """
    Request model for tool execution.
    
    This model defines the structure of requests to tool execution endpoints.
    It includes a data field that can contain any JSON-serializable data.
    
    Attributes:
        data (Dict[str, Any]): Dictionary containing the tool's input data.
    """
    data: Dict[str, Any]

class FastMCP:
    """
    FastAPI-based MCP server implementation.
    
    This class provides a FastAPI-based server for the MCP agent system.
    It handles tool registration, execution, and API key authentication.
    
    Attributes:
        name (str): Name of the agent.
        port (int): Port to run the server on.
        api_key (Optional[str]): Optional API key for authentication.
        tools (Dict[str, Callable]): Dictionary of registered tools.
        app (FastAPI): FastAPI application instance.
    
    Methods:
        __init__(name, port, api_key): Initialize the server.
        register_tool(name, func): Register a tool with the server.
        run(): Start the server.
    """
    
    def __init__(self, name: str, port: int = 8000, api_key: Optional[str] = None):
        """
        Initialize the FastMCP server.
        
        Sets up the server with a specified name, port, and optional API key for authentication.
        Creates a FastAPI application instance and defines basic endpoints like health check
        and tool execution.
        
        Args:
            name (str): Name of the agent.
            port (int): Port to run the server on.
            api_key (Optional[str]): Optional API key for authentication.
        """
        self.name = name
        self.port = port
        self.api_key = api_key
        self.tools: Dict[str, Callable] = {}
        
        # Create FastAPI app with a descriptive title
        self.app = FastAPI(title=f"{name} MCP Server")
        
        # Add health check endpoint for monitoring server status
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint.
            
            Returns:
                Dictionary containing server status and agent name.
            """
            return {"status": "healthy", "agent": name}
        
        # Add tool execution endpoint for running registered tools
        @self.app.post("/tools/{tool_name}")
        async def execute_tool(
            tool_name: str,
            request: ToolRequest,
            api_key: Optional[str] = Header(None, alias="API-Key")
        ):
            """Tool execution endpoint.
            
            This endpoint executes a registered tool with the provided data.
            It includes API key authentication if configured.
            
            Args:
                tool_name: Name of the tool to execute.
                request: Tool execution request.
                api_key: Optional API key from header.
                
            Returns:
                Tool execution result.
                
            Raises:
                HTTPException: If authentication fails or tool not found.
            """
            # Check API key if configured for security
            if self.api_key and api_key != self.api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Check if tool exists in registered tools
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
            
            # Execute tool with provided data
            try:
                result = self.tools[tool_name](request.data)
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def register_tool(self, name: str, func: Callable) -> None:
        """
        Register a tool with the server.
        
        This method registers a tool function with the server, making it available
        through the API for execution.
        
        Args:
            name (str): Name of the tool.
            func (Callable): Tool function to register.
        
        Raises:
            ValueError: If tool name is already registered.
        """
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered")
        
        self.tools[name] = func
        print(f"Registered tool '{name}' for {self.name}")
    
    def run(self) -> None:
        """
        Run the FastAPI server.
        
        This method starts the FastAPI server on the configured port using Uvicorn
        as the ASGI server implementation.
        """
        print(f"Starting {self.name} server on port {self.port}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port) 