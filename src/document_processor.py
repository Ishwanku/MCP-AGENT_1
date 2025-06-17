import os
import asyncio
import aiohttp
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, TypedDict, AsyncIterator
from langgraph.graph import StateGraph, END
import time
from docx import Document
from dotenv import load_dotenv
from mcp.core.config import settings

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress logging from other modules
logging.getLogger('aiohttp').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

# Define state types for LangGraph for each node
class FolderState(TypedDict):
    folder_name: str
    documents: List[str]
    summary: str
    section_name: str

class DocumentState(TypedDict):
    input_dir: str
    folders: List[FolderState]
    output_file: str
    final_summary_path: str
    error: str

# Read the input document and return the plain text
async def get_document_content(doc_path: Path) -> str:
    """Get document content from cache or read from disk."""
    doc = Document(doc_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

# Process a single document reads the .docx file and send the prompt to LLM with max 5000 chracters to get summary and important info.
async def process_single_document(session: aiohttp.ClientSession, doc_path: Path) -> Dict[str, Any]:
    """Process a single document and extract important information."""
    try:
        start_time = time.time()
        logger.info(f"Starting processing of document {doc_path.name} at {time.strftime('%H:%M:%S')}")

        # Get document content from cache
        text_content = await get_document_content(doc_path)
        
        # Create prompt for LLM
        prompt = f"""
        Analyze this document and provide:
        1. Executive Summary: A concise summary of the main content
        2. Important Information: Critical points that need special attention

        Document: {doc_path.name}
        Content: {text_content[:5000]}  # Limit content length
        """
        
        # Make LLM request with retry mechanism
        data = {
            "prompt": prompt,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        async with session.post(
            "http://127.0.0.1:8000/tools/llm",
            headers={"Content-Type": "application/json", "API-Key": os.getenv("DOCUMENT_AGENT_API_KEY")},
            json=data
        ) as response:
            if response.status == 200:
                llm_result = await response.json()
                return {
                    "status": "success",
                    "document_name": doc_path.name,
                    "original_document_name": doc_path.name,
                    "analysis": llm_result.get("content", ""),
                    "error": ""
                }
            else:
                error_msg = f"Error processing document {doc_path.name}: {await response.text()}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "document_name": doc_path.name,
                    "original_document_name": doc_path.name,
                    "analysis": "",
                    "error": error_msg
                }
    except Exception as e:
        error_msg = f"Error processing document {doc_path.name}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "document_name": doc_path.name,
            "original_document_name": doc_path.name,
            "analysis": "",
            "error": error_msg
        }

# Fetch the subfolders from the input folder.
async def discover_folders(input_dir: Path) -> AsyncIterator[Path]:
    """Asynchronously discover folders in the input directory."""
    for folder_path in input_dir.iterdir():
        if folder_path.is_dir():
            yield folder_path

# Process all documents parallely from the single folder and make a result + combined folder-level summary using other LLM prompt and return it in structured result.
async def process_single_folder(session: aiohttp.ClientSession, folder_path: Path) -> Dict[str, Any]:
    """Process a single folder and all its documents in parallel."""
    try:
        folder_name = folder_path.name
        logger.info(f"Starting processing of folder {folder_name} at {time.strftime('%H:%M:%S')}")
        
        # Get all .docx files in the folder
        docx_files = [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() == '.docx']
        if not docx_files:
            logger.warning(f"No .docx files found in folder: {folder_path}")
            return {
                "folder_name": folder_name,
                "document_analyses": [],
                "summary": "",
                "error": f"No .docx files found in folder: {folder_path}"
            }
        
        # Process all documents in parallel
        doc_tasks = [process_single_document(session, doc_path) for doc_path in docx_files]
        doc_results = await asyncio.gather(*doc_tasks)
        
        # Filter successful results
        successful_results = [r for r in doc_results if r["status"] == "success"]
        if not successful_results:
            logger.warning(f"No documents were successfully processed in folder: {folder_path}")
            return {
                "folder_name": folder_name,
                "document_analyses": [],
                "summary": "",
                "error": f"No documents were successfully processed in folder: {folder_path}"
            }
        
        # Generate folder summary with retry mechanism
        summary_prompt = f"""
        Create a comprehensive summary of these related documents:
        {chr(10).join([f"- {r['original_document_name']}: {r['analysis']}" for r in successful_results])}

        Focus on:
        1. Executive Summary: Provide a clear, concise summary of the entire document set
        2. Important Information: List any critical points or information that requires special attention
        """
        
        # Get summary from LLM with retry mechanism
        summary_data = {
            "prompt": summary_prompt,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        async with session.post(
            "http://127.0.0.1:8000/tools/llm",
            headers={"Content-Type": "application/json", "API-Key": os.getenv("DOCUMENT_AGENT_API_KEY")},
            json=summary_data
        ) as response:
            if response.status == 200:
                summary_result = await response.json()
                return {
                    "folder_name": folder_name,
                    "document_analyses": successful_results,
                    "summary": summary_result.get("content", ""),
                    "error": ""
                }
            else:
                error_msg = f"Error generating summary: {await response.text()}"
                logger.error(error_msg)
                return {
                    "folder_name": folder_name,
                    "document_analyses": successful_results,
                    "summary": "",
                    "error": error_msg
                }
    except Exception as e:
        error_msg = f"Error processing folder {folder_path}: {str(e)}"
        logger.error(error_msg)
        return {
            "folder_name": folder_name,
            "document_analyses": [],
            "summary": "",
            "error": error_msg
        }

# Process all folders in parallel using asynio.create_task() and store the summary and document of each folder into state["folders"] also handles the error if any folder fails
async def process_all_folders(state: DocumentState) -> DocumentState:
    """Process all folders and their documents in parallel."""
    try:
        start_time = time.time()
        logger.info(f"Starting parallel processing of all folders at {time.strftime('%H:%M:%S')}")

        # Validate input directory
        input_dir = Path(state["input_dir"])
        if not input_dir.exists():
            state["error"] = f"Input directory not found: {input_dir}"
            return state

        # Process folders as they are discovered
        async with aiohttp.ClientSession() as session:
            tasks = []
            async for folder_path in discover_folders(input_dir):
                task = asyncio.create_task(process_single_folder(session, folder_path))
                tasks.append(task)
            
            folder_results = await asyncio.gather(*tasks)

        # Update state with results
        state["folders"] = [
            {
                "folder_name": result["folder_name"],
                "document_analyses": result["document_analyses"],
                "summary": result["summary"],
                "section_name": result["folder_name"]
            }
            for result in folder_results
        ]

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Completed processing all folders in {duration:.2f} seconds")
        
        return state
    except Exception as e:
        state["error"] = str(e)
        return state

# Fetch the document paths + summary from each successfully processed folders and send them all to /tools/merge_documents API then generate the final merge DOCX file and store it in state["final_summary_path"]
async def create_final_document(state: DocumentState) -> DocumentState:
    """Create the final merged document with all folder summaries."""
    try:
        start_time = time.time()
        logger.info(f"Starting final document creation at {time.strftime('%H:%M:%S')}")

        url = f"{settings.API_BASE_URL}/tools/merge_documents"
        headers = {
            "Content-Type": "application/json",
            "API-Key": settings.DOCUMENT_AGENT_API_KEY
        }
        
        # Create output directory if it doesn't exist
        output_dir = Path(settings.OUTPUT_DIR).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare document sets for merging
        document_sets = []
        input_dir = Path(state["input_dir"]).resolve()
        
        for i, folder in enumerate(state["folders"], 1):
            if not folder.get("document_analyses"):
                logger.warning(f"Skipping folder {folder['folder_name']} - no document analyses available")
                continue
                
            # Get full paths for documents
            folder_path = input_dir / folder["folder_name"]
            document_paths = []
            document_names = []  # Store just the file names
            for doc in folder["document_analyses"]:
                doc_path = folder_path / doc["original_document_name"]
                if not doc_path.exists():
                    logger.error(f"Document not found: {doc_path}")
                    continue
                document_paths.append(str(doc_path))
                document_names.append(doc["original_document_name"])  # Store just the name
            
            if not document_paths:
                logger.warning(f"No valid documents found in folder {folder['folder_name']}")
                continue
            
            # Log the documents being included in this set (using just file names)
            logger.info(f"Preparing document set {i}: {folder['folder_name']}")
            logger.info(f"Documents in set: {document_names}")  # Log just the names
            
            # Use full document paths for merging but names for display
            document_sets.append({
                "name": folder['folder_name'],  # Remove section number prefix
                "documents": document_paths,  # Keep full paths for actual merging
                "document_names": document_names,  # Store names for display
                "summary": folder.get("summary", "No summary available"),
                "summary_type": "comprehensive",
                "include_sections": [
                    "executive_summary",
                    "important_information"
                ]
            })
        
        if not document_sets:
            error_msg = "No document sets available for merging"
            logger.error(error_msg)
            state["error"] = error_msg
            return state
        
        # Log the final document sets being sent for merging (using just file names)
        logger.info(f"Preparing to merge {len(document_sets)} document sets")
        for i, doc_set in enumerate(document_sets, 1):
            logger.info(f"Set {i}: {doc_set['name']} with documents: {doc_set['document_names']}")
        
        data = {
            "input_dir": str(input_dir),
            "output_file": str(output_dir / state["output_file"]),
            "document_sets": document_sets
        }
        
        # Log the merge request
        logger.info(f"Sending merge request to {url}")
        logger.info(f"Output will be saved to: {data['output_file']}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        result = await response.json()
                        state["final_summary_path"] = result.get("output_path", "")
                        end_time = time.time()
                        duration = end_time - start_time
                        logger.info(f"Successfully created final document in {duration:.2f} seconds")
                        logger.info(f"Final document saved at: {state['final_summary_path']}")
                    else:
                        error_msg = f"Error creating final document: {response_text}"
                        logger.error(error_msg)
                        logger.error(f"Response status: {response.status}")
                        state["error"] = error_msg
            except Exception as e:
                error_msg = f"Error during merge request: {str(e)}"
                logger.error(error_msg)
                state["error"] = error_msg
        
        return state
    except Exception as e:
        error_msg = f"Error in final document creation: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        return state

# Main function to set the LangGraph Workflow by setting (Nodes: process_folders → create_document → END) parallel processing using app.ainvoke()
async def main():
    """Main function to run the parallel document processing workflow."""
    try:
        # Get input directory from environment variable
        input_dir = os.getenv("INPUT_DIR", "documents")
        output_file = f"final_merged_document_{time.strftime('%Y%m%d_%H%M%S')}.docx"
        
        logger.info(f"Starting document merge process at {datetime.now()}")
        logger.info(f"Input directory: {input_dir}")
        
        # Initialize state
        initial_state = {
            "input_dir": input_dir,
            "folders": [],
            "output_file": output_file,
            "final_summary_path": "",
            "error": ""
        }
        
        # Create workflow graph
        workflow = StateGraph(DocumentState)
        
        # Add nodes
        workflow.add_node("process_folders", process_all_folders)
        workflow.add_node("create_document", create_final_document)
        
        # Define edges
        workflow.add_edge("process_folders", "create_document")
        workflow.add_edge("create_document", END)
        
        # Set entry point
        workflow.set_entry_point("process_folders")
        
        # Compile workflow
        app = workflow.compile()
        
        # Run workflow
        final_state = await app.ainvoke(initial_state)
        
        if final_state["error"]:
            logger.error(f"Error in workflow: {final_state['error']}")
        else:
            logger.info(f"Successfully created merged document at: {final_state['final_summary_path']}")
            logger.info(f"Document merge process completed at {datetime.now()}")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise

# Run the main in starting of script using asyncio.run()  
if __name__ == "__main__":
    print("Starting parallel document processing workflow...")
    asyncio.run(main())
    print("Workflow completed.") 