import os
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from ..core.document_parser import DocumentParser

# Initialize FastAPI application with a descriptive title for API documentation
app = FastAPI(title="Document Merge Agent")


# Document Set model defined by using pydantic
class DocumentSet(BaseModel):
    name: str
    documents: List[str]


# MergeRequest model (Payload structure from client side) 
class MergeRequest(BaseModel):
    input_dir: str
    document_sets: List[DocumentSet]
    output_file: str


# MergeResponse model (Response structure from server side)
class MergeResponse(BaseModel):
    status: str
    message: str
    output_path: str
    set_summaries: List[dict] = []


# Root test endpoint (check by using http://localhost:8000/docs)
@app.get("/")
async def root():
    return {"message": "Welcome to MCP Document Merge Agent. Available endpoints: /docs for API documentation, /tools/merge_documents for document merging."}

# This is the Main POST endpoint: /tools/merge_documents
@app.post("/tools/merge_documents", response_model=MergeResponse)
async def merge_documents(
    request: MergeRequest,
    api_key: str = Header(..., description="API Key for authentication")
) -> MergeResponse:
    try:
        # Validate API key against environment variable for security
        if api_key != os.getenv("DOCUMENT_AGENT_API_KEY"):
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Convert input directory to Path object and check if it exists
        input_dir = Path(request.input_dir)
        if not input_dir.exists():
            raise HTTPException(status_code=404, detail=f"Input directory not found: {input_dir}")
        
        # Validate that document sets are provided in the request
        if not request.document_sets:
            raise HTTPException(status_code=400, detail="No document sets specified")
        
        # Check if all specified documents exist in the input directory
        for doc_set in request.document_sets:
            for doc_name in doc_set.documents:
                doc_path = input_dir / doc_name
                if not doc_path.exists():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document not found: {doc_name} in set {doc_set.name}"
                    )
        
        # Create output directory if it doesn't exist, using environment variable or default
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        output_dir.mkdir(exist_ok=True)
        
        # Initialize document parser to handle the merging process
        parser = DocumentParser()
        
        # Convert document sets to the format expected by the parser
        doc_sets = [{"name": ds.name, "documents": ds.documents} for ds in request.document_sets]
        
        # Create new Word document with summaries for each set
        merged_doc = parser.create_context_document(doc_sets, input_dir, request.output_file)
        
        # Save the merged document to the output directory
        output_path = output_dir / request.output_file
        merged_doc.save(output_path)
        
        # Process each set to get summaries
        set_summaries = []
        for doc_set in doc_sets:
            set_info = parser.process_document_set(doc_set, input_dir)
            set_summaries.append({
                "set_name": set_info["set_name"],
                "summary": set_info["summary"],
                "documents": set_info["documents"]
            })
        
        # Return success response with details of the operation
        return MergeResponse(
            status="success",
            message="Documents merged successfully with set summaries",
            output_path=str(output_path),
            set_summaries=set_summaries
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