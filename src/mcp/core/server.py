from fastapi import FastAPI, HTTPException, Header
from typing import Dict, Any, Callable, Optional
import uvicorn
from pydantic import BaseModel

# This is a request model which is use to validate JSON data while calling a tool 
class ToolRequest(BaseModel):
    data: Dict[str, Any]

# This is a modular FastAPI server class that registers tools and exposes them as API endpoints   
class FastMCP:

    
    def __init__(self, name: str, port: int = 8000, api_key: Optional[str] = None):

        self.name = name
        self.port = port
        self.api_key = api_key
        self.tools: Dict[str, Callable] = {}
        
        # Create FastAPI app with a descriptive title
        self.app = FastAPI(title=f"{name} MCP Server")
        
        # Add health check endpoint for monitoring server status
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "agent": name}
        
        # Add tool execution endpoint for running registered tools
        @self.app.post("/tools/{tool_name}")
        async def execute_tool(
            tool_name: str,
            request: ToolRequest,
            api_key: Optional[str] = Header(None, alias="API-Key")
        ):
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
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered")
        
        self.tools[name] = func
        print(f"Registered tool '{name}' for {self.name}")
    
    def run(self) -> None:
        print(f"Starting {self.name} server on port {self.port}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port) 