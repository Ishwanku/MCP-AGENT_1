import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from ..core.document_parser import DocumentParser
from ..core.config import Settings
import asyncio
import logging

# Initialize settings
settings = Settings()

# Initialize FastAPI application with a descriptive title for API documentation
app = FastAPI(title="Document Merge Agent")

# Configure logger
logger = logging.getLogger(__name__)

# Document Set model defined by using pydantic
class DocumentSet(BaseModel):
    name: str
    documents: List[str]
    summary_type: str = settings.DEFAULT_SUMMARY_TYPE
    include_sections: List[str] = settings.DEFAULT_INCLUDE_SECTIONS


# MergeRequest model (Payload structure from client side) 
class MergeRequest(BaseModel):
    input_dir: str
    output_file: Optional[str] = None
    document_sets: List[DocumentSet]


# MergeResponse model (Response structure from server side)
class MergeResponse(BaseModel):
    status: str
    message: str
    output_path: Optional[str] = None
    set_summaries: List[Dict[str, Any]]


# Add LLM request and response models
class LLMRequest(BaseModel):
    prompt: str
    max_tokens: int = settings.LLM_DEFAULT_MAX_TOKENS
    temperature: float = settings.LLM_DEFAULT_TEMPERATURE

class LLMResponse(BaseModel):
    status: str
    content: str
    error: str = ""


# Root test endpoint (check by using http://localhost:8000/docs)
@app.get("/")
async def root():
    return {"message": "Welcome to MCP Document Merge Agent. Available endpoints: /docs for API documentation, /tools/merge_documents for document merging."}

# 5 This is the Main POST endpoint: /tools/merge_documents
@app.post("/tools/merge_documents", response_model=MergeResponse)
async def merge_documents(
    request: MergeRequest,
    api_key: str = Header(..., description="API Key for authentication")
) -> MergeResponse:
    try:
        # Validate API key
        if api_key != settings.DOCUMENT_AGENT_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Initialize document parser
        parser = DocumentParser()
        
        # Process each document set
        set_summaries = []
        input_dir = Path(request.input_dir)
        
        for idx, doc_set in enumerate(request.document_sets, 1):
            try:
                # Validate documents exist
                for doc_name in doc_set.documents:
                    doc_path = input_dir / doc_name
                    if not doc_path.exists():
                        raise HTTPException(
                            status_code=404,
                            detail=f"Document not found: {doc_name} in set {doc_set.name}"
                        )
                
                # Process the document set
                set_info = await parser.process_document_set(
                    {
                        "name": doc_set.name,
                        "documents": doc_set.documents
                    },
                    input_dir
                )
                
                if not set_info.get("summary"):
                    logger.warning(f"No summary generated for set {doc_set.name}")
                    set_info["summary"] = "No summary available - please check document contents"
                
                set_summaries.append({
                    "set_name": f"Section {idx}: {doc_set.name}",
                    "summary": set_info["summary"],
                    "documents": set_info["documents"]
                })
                
                logger.info(f"Successfully processed set {doc_set.name}")
                
            except Exception as e:
                logger.error(f"Error processing document set {doc_set.name}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing document set {doc_set.name}: {str(e)}"
                )
        
        if not set_summaries:
            raise HTTPException(
                status_code=500,
                detail="No document sets were successfully processed"
            )
        
        # Create output document if specified
        output_path = None
        if request.output_file:
            try:
                output_path = str(Path(request.output_file).resolve())
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                doc = parser.create_context_document(set_summaries, input_dir, output_path)
                doc.save(output_path)
                
                if not Path(output_path).exists():
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create output document"
                    )
                    
                logger.info(f"Successfully created output document at {output_path}")
                
            except Exception as e:
                logger.error(f"Error creating output document: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error creating output document: {str(e)}"
                )
        
        return MergeResponse(
            status="success",
            message="Documents processed successfully",
            output_path=output_path,
            set_summaries=set_summaries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in merge_documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

# Add LLM endpoint
@app.post("/tools/llm", response_model=LLMResponse)
async def llm_endpoint(
    request: LLMRequest,
    api_key: str = Header(..., description="API Key for authentication")
) -> LLMResponse:
    try:
        # Validate API key
        if api_key != settings.DOCUMENT_AGENT_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Initialize LLM client
        from ..core.llm_client import LLMClient
        
        llm_client = LLMClient(settings)
        
        # Generate content
        content = llm_client.generate_content(request.prompt)
        
        return LLMResponse(
            status="success",
            content=content
        )
        
    except Exception as e:
        return LLMResponse(
            status="error",
            content="",
            error=str(e)
        )

if __name__ == "__main__":
    # Entry point to run the FastAPI server directly if this module is executed.
    import uvicorn
    # Inform user about tool registration and server startup
    print("Registered tool 'merge_documents' for Document Merge Agent")
    print(f"Starting Document Merge Agent server on port {settings.DOCUMENT_AGENT_PORT}")
    # Start the Uvicorn server with configuration from environment variables
    uvicorn.run(app, host=settings.host, port=settings.port)