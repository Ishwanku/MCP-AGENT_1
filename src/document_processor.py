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
from mcp.core.utils import retry_llm_call

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
    try:
        doc = Document(doc_path)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        if not text:
            logger.warning(f"No readable text found in {doc_path.name}")
        return text
    except Exception as e:
        logger.error(f"Error reading document {doc_path.name}: {str(e)}")
        return ""

# Split document into overlapping chunks with metadata
def chunk_document(text: str, doc_name: str, chunk_size: int = 4000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """Split document into overlapping chunks with document metadata."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        if start > 0:
            start = start - chunk_overlap
        if end >= text_length:
            chunk = text[start:]
            chunks.append({
                "document": doc_name,
                "chunk_index": len(chunks) + 1,
                "content": chunk
            })
            break

        last_period = text.rfind(".", start, end)
        last_newline = text.rfind("\n", start, end)
        break_point = max(last_period, last_newline)
        if break_point > start:
            end = break_point + 1

        chunk = text[start:end]
        chunks.append({
            "document": doc_name,
            "chunk_index": len(chunks) + 1,
            "content": chunk
        })
        start = end

    if not chunks:
        logger.warning(f"No chunks created for {doc_name} with text of {text_length} chars")
    return chunks

# Process a single document with chunking and retry logic
async def process_single_document(session: aiohttp.ClientSession, doc_path: Path) -> Dict[str, Any]:
    """Process a single document by chunking content and extracting important information."""
    try:
        logger.info(f"Starting processing of document {doc_path.name}")

        # Get document content
        text_content = await get_document_content(doc_path)
        if not text_content:
            return {
                "status": "error",
                "document_name": doc_path.name,
                "original_document_name": doc_path.name,
                "analysis": "No text content extracted from document",
                "error": "Empty or unreadable document",
                "chunk_analyses": []
            }
        
        # Split document into chunks with metadata
        chunks = chunk_document(text_content, doc_path.name)
        logger.info(f"Split {doc_path.name} into {len(chunks)} chunks")
        chunk_analyses = []

        # Define HTTP request function with retry decorator
        @retry_llm_call(
            max_attempts=3,
            initial_wait=2.0,
            max_wait=8.0,
            exceptions=(aiohttp.ClientResponseError, aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, Exception),
            result_predicate=lambda result: not result.get("content") or result.get("content") == "No response generated",
            log_context=f"HTTP request for chunk of {doc_path.name}"
        )
        async def make_llm_request(prompt: str, chunk_index: int) -> Dict[str, Any]:
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
                response.raise_for_status()
                llm_result = await response.json()
                if not llm_result.get("content") or llm_result.get("content") == "No response generated":
                    logger.warning(f"No content in LLM response for chunk {chunk_index} of {doc_path.name}")
                return llm_result

        # Process each chunk
        for chunk in chunks:
            chunk_index = chunk["chunk_index"]
            chunk_content = chunk["content"]

            prompt = f"""
            Analyze this part of the document (Part {chunk_index} of {len(chunks)}) and provide:
            1. A concise summary of the main content
            2. Any critical or important information that needs special attention

            Document: {doc_path.name}
            Content: {chunk_content}
            """
            
            try:
                llm_result = await make_llm_request(prompt, chunk_index)
                chunk_analyses.append({
                    "document": doc_path.name,
                    "chunk_index": chunk_index,
                    "analysis": llm_result.get("content", f"Error: No content in LLM response")
                })
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk_index} of {doc_path.name} after retries: {str(e)}")
                chunk_analyses.append({
                    "document": doc_path.name,
                    "chunk_index": chunk_index,
                    "analysis": f"Error: {str(e)}"
                })

        # Check if any valid analyses were generated
        valid_analyses = [a for a in chunk_analyses if not a["analysis"].startswith("Error:")]
        if not valid_analyses:
            logger.warning(f"No valid analyses generated for {doc_path.name}")
            return {
                "status": "error",
                "document_name": doc_path.name,
                "original_document_name": doc_path.name,
                "analysis": "No valid analysis available - all chunks failed processing",
                "error": "No valid chunk analyses generated",
                "chunk_analyses": chunk_analyses
            }

        # Create final summary of all chunks
        summary_prompt = f"""
        Create a comprehensive analysis of this document by combining the analyses of its parts.
        Focus on two main aspects:
        1. Executive Summary: Provide a clear, concise summary of the entire document
        2. Important Information: List any critical points, key findings, or information that requires special attention

        Document: {doc_path.name}
        Part Analyses:
        {chr(10).join([f"Part {a['chunk_index']}: {a['analysis']}" for a in chunk_analyses])}
        """
        
        try:
            llm_result = await make_llm_request(summary_prompt, chunk_index=0)  # chunk_index=0 for document summary
            final_analysis = llm_result.get("content", "No analysis available")
            logger.info(f"Completed processing of document {doc_path.name}")
            return {
                "status": "success",
                "document_name": doc_path.name,
                "original_document_name": doc_path.name,
                "analysis": final_analysis,
                "error": "",
                "chunk_analyses": chunk_analyses
            }
        except Exception as e:
            logger.error(f"Failed to combine chunk analyses for {doc_path.name} after retries: {str(e)}")
            return {
                "status": "error",
                "document_name": doc_path.name,
                "original_document_name": doc_path.name,
                "analysis": "",
                "error": str(e),
                "chunk_analyses": chunk_analyses
            }
    except Exception as e:
        logger.error(f"Error processing document {doc_path.name}: {str(e)}")
        return {
            "status": "error",
            "document_name": doc_path.name,
            "original_document_name": doc_path.name,
            "analysis": "",
            "error": str(e),
            "chunk_analyses": []
        }
# Fetch the subfolders from the input folder
async def discover_folders(input_dir: Path) -> AsyncIterator[Path]:
    """Asynchronously discover folders in the input directory."""
    for folder_path in input_dir.iterdir():
        if folder_path.is_dir():
            yield folder_path

# Process all documents in parallel from a single folder
async def process_single_folder(session: aiohttp.ClientSession, folder_path: Path) -> Dict[str, Any]:
    """Process a single folder and all its documents in parallel."""
    try:
        folder_name = folder_path.name
        logger.info(f"Starting processing of folder {folder_name}")
        
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
        
        for attempt in range(1, 4):
            try:
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
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        logger.error(f"Error generating summary for {folder_name} (attempt {attempt}): {error_msg}")
                        if attempt == 3:
                            return {
                                "folder_name": folder_name,
                                "document_analyses": successful_results,
                                "summary": "",
                                "error": error_msg
                            }
                        await asyncio.sleep(2 ** attempt)
            except Exception as e:
                error_msg = f"Exception: {str(e)}"
                logger.error(f"Error generating summary for {folder_name} (attempt {attempt}): {error_msg}")
                if attempt == 3:
                    return {
                        "folder_name": folder_name,
                        "document_analyses": successful_results,
                        "summary": "",
                        "error": error_msg
                    }
                await asyncio.sleep(2 ** attempt)
    except Exception as e:
        error_msg = f"Error processing folder {folder_path}: {str(e)}"
        logger.error(error_msg)
        return {
            "folder_name": folder_name,
            "document_analyses": [],
            "summary": "",
            "error": error_msg
        }

# Process all folders in parallel (NODE 1)
async def process_all_folders(state: DocumentState) -> DocumentState:
    """Process all folders and their documents in parallel."""
    try:
        logger.info(f"Starting parallel processing of all folders")

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

        logger.info(f"Completed processing all folders")
        
        return state
    except Exception as e:
        state["error"] = str(e)
        return state

# Create the final merged document (NODE 2)
async def create_final_document(state: DocumentState) -> DocumentState:
    """Create the final merged document with all folder summaries."""
    try:
        logger.info(f"Starting final document creation")

        url = f"{settings.API_BASE_URL}/tools/merge_documents"
        headers = {
            "Content-Type": "application/json",
            "API-Key": settings.DOCUMENT_AGENT_API_KEY
        }
        
        # Create output directory
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
            document_names = []
            chunk_analyses = []
            for doc in folder["document_analyses"]:
                doc_path = folder_path / doc["original_document_name"]
                if not doc_path.exists():
                    logger.error(f"Document not found: {doc_path}")
                    continue
                document_paths.append(str(doc_path))
                document_names.append(doc["original_document_name"])
                chunk_analyses.extend(doc.get("chunk_analyses", []))
            
            if not document_paths:
                logger.warning(f"No valid documents found in folder {folder['folder_name']}")
                continue
            
            document_sets.append({
                "name": folder['folder_name'],
                "documents": document_paths,
                "document_names": document_names,
                "summary": folder.get("summary", "No summary available"),
                "summary_type": "comprehensive",
                "include_sections": [
                    "executive_summary",
                    "important_information"
                ],
                "chunk_analyses": chunk_analyses
            })
        
        if not document_sets:
            error_msg = "No document sets available for merging"
            logger.error(error_msg)
            state["error"] = error_msg
            return state
        
        data = {
            "input_dir": str(input_dir),
            "output_file": str(output_dir / state["output_file"]),
            "document_sets": document_sets
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(1, 4):
                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            state["final_summary_path"] = result.get("output_path", "")
                            logger.info(f"Final document saved at: {state['final_summary_path']}")
                            return state
                        else:
                            error_msg = f"Error creating final document: {await response.text()}"
                            logger.error(f"Merge request failed (attempt {attempt}): {error_msg}")
                            if attempt == 3:
                                state["error"] = error_msg
                                return state
                            await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    error_msg = f"Error during merge request: {str(e)}"
                    logger.error(f"Merge request failed (attempt {attempt}): {error_msg}")
                    if attempt == 3:
                        state["error"] = error_msg
                        return state
                    await asyncio.sleep(2 ** attempt)
        
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
        
        # Compiles graph into an executable app.
        app = workflow.compile()
        
        # Run workflow
        final_state = await app.ainvoke(initial_state)
        
        if final_state["error"]:
            logger.error(f"Error in workflow: {final_state['error']}")
        else:
            logger.info(f"Successfully created merged document at: {final_state['final_summary_path']}")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    print("Starting parallel document processing workflow...")
    asyncio.run(main())
    print("Workflow completed.")