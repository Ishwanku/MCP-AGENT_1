"""
MCP Document Merge Agent

This module defines the core FastAPI application for the MCP Document Merge Agent.
It provides endpoints for merging multiple document types (DOCX, PDF, TXT, PPTX) into a single
Word document, with optional summarization using configurable LLM providers.

Key Features:
- Handles HTTP requests for document merging operations.
- Supports multiple document formats through parsing utilities.
- Integrates with LLM clients for content summarization or context extraction.
- Provides secure API access with optional API key authentication.

Usage:
    This module is launched via `run.py`, which starts the FastAPI server.
    Clients can interact with the server via HTTP POST requests to the defined endpoints,
    such as `/tools/merge_documents` for merging documents.

Configuration:
    Settings are loaded from environment variables or a `.env` file, including
    DOCUMENT_AGENT_API_KEY for authentication and OUTPUT_DIR for result storage.
"""

import os
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from ..core.document_parser import DocumentParser

# Initialize FastAPI application with a descriptive title for API documentation
app = FastAPI(title="Document Merge Agent")


class MergeRequest(BaseModel):
    """
    Request model for document merge operation.

    This class defines the structure of the JSON payload expected by the merge endpoint.
    It includes paths and filenames necessary for the merging process.

    Attributes:
        input_dir (str): Directory containing input documents to be merged.
        output_file (str): Name of the output file where the merged document will be saved.
        context_docs (List[str]): List of context document filenames to merge.
    """
    input_dir: str
    output_file: str
    context_docs: List[str]


class MergeResponse(BaseModel):
    """
    Response model for document merge operation.

    This class defines the structure of the JSON response returned by the merge endpoint,
    providing feedback on the operation's success or failure.

    Attributes:
        status (str): Status of the merge operation ('success' or error description).
        message (str): Informational message about the operation result.
        output_path (str): Path to the merged output document if successful.
    """
    status: str
    message: str
    output_path: str


@app.get("/")
async def root():
    """Root endpoint providing a welcome message and API endpoint information."""
    return {"message": "Welcome to MCP Document Merge Agent. Available endpoints: /docs for API documentation, /tools/merge_documents for document merging."}


@app.post("/tools/merge_documents", response_model=MergeResponse)
async def merge_documents(
    request: MergeRequest,
    api_key: str = Header(..., description="API Key for authentication")
) -> MergeResponse:
    """
    Merge multiple documents into a single Word document with context.

    This endpoint handles the document merging process. It validates the API key for authentication,
    checks the existence of input files and directories, initializes a DocumentParser to create
    a merged document with consistent styles, and saves the result to the specified output file.

    Args:
        request (MergeRequest): Request object containing input directory, output file, and context documents.
        api_key (str): API key for authentication, passed via request header.

    Returns:
        MergeResponse: Object containing the status, message, and output path of the merged document.

    Raises:
        HTTPException: For authentication errors (401), missing files (404), invalid input (400),
                       or processing errors (500).
    """
    try:
        # Validate API key against environment variable for security
        if api_key != os.getenv("DOCUMENT_AGENT_API_KEY"):
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Convert input directory to Path object and check if it exists
        input_dir = Path(request.input_dir)
        if not input_dir.exists():
            raise HTTPException(status_code=404, detail=f"Input directory not found: {input_dir}")
        
        # Validate that context documents are provided in the request
        if not request.context_docs:
            raise HTTPException(status_code=400, detail="No context documents specified")
        
        # Check if all specified context documents exist in the input directory
        context_files = []
        for doc_name in request.context_docs:
            doc_path = input_dir / doc_name
            if not doc_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Context document not found: {doc_name}"
                )
            context_files.append(doc_path)
        
        # Create output directory if it doesn't exist, using environment variable or default
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        output_dir.mkdir(exist_ok=True)
        
        # Initialize document parser to handle the merging process
        parser = DocumentParser()
        
        # Create new Word document with context from provided files
        merged_doc = parser.create_context_document(context_files, request.output_file)
        
        # Ensure styles are initialized in the merged document for consistent formatting
        parser._init_document_styles(merged_doc)
        
        # Save the merged document to the output directory
        output_path = output_dir / request.output_file
        merged_doc.save(output_path)
        
        # Return success response with details of the operation
        return MergeResponse(
            status="success",
            message="Documents merged successfully with context",
            output_path=str(output_path)
        )
        
    except Exception as e:
        # Catch any processing errors and return as HTTP 500 error
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Entry point to run the FastAPI server directly if this module is executed
    import uvicorn
    # Inform user about tool registration and server startup
    print("Registered tool 'merge_documents' for Document Merge Agent")
    print(f"Starting Document Merge Agent server on port {os.getenv('DOCUMENT_AGENT_PORT', 8000)}")
    # Start the Uvicorn server with configuration from environment variables
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("DOCUMENT_AGENT_PORT", 8000)))