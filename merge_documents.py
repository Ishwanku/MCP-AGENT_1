"""
MCP Document Merge Agent Client Script

This script serves as a client to interact with the MCP Document Merge Agent API.
It sends requests to the document merging endpoint to combine multiple documents
into a single Word document, handling the input directory, output file naming,
and context document selection.

Key Features:
- Automatically gathers document files from a specified input directory.
- Sends HTTP POST requests to the merge endpoint with necessary parameters.
- Handles API responses and errors, providing user feedback.
- Configurable via command-line arguments or environment variables.

Usage:
    Run this script with `python merge_documents.py` to merge documents from the default
    input directory (documents/) into a specified output file. Customize input/output
    via command-line arguments if needed.

Configuration:
    Ensure the MCP Agent server is running (via `python run.py`) before using this script.
    API endpoint, port, and API key should match the server configuration (see .env file).
"""

import requests
import json
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file for API key and configuration
load_dotenv()

# Add tracing for debugging flow to track script execution
print("Starting merge_documents.py execution")

def merge_documents(input_dir: str, output_file: str, context_docs: list) -> None:
    """Merge documents using the MCP Agent.
    
    This function prepares a request to the MCP Agent API endpoint for document merging.
    It validates the input directory, sets up headers with the API key, and sends a POST
    request with the necessary data. It then processes the server's response to inform
    the user of success or failure.
    
    Args:
        input_dir (str): Directory containing input text files to be merged.
        output_file (str): Name of the output Word document where merged content will be saved.
        context_docs (list): List of document names to use for context during merging.
    """
    print(f"Starting document merge process with input directory: {input_dir}")
    # Ensure the input directory exists to prevent errors
    if not Path(input_dir).exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Prepare the request with the API endpoint URL and necessary headers
    url = "http://127.0.0.1:8000/tools/merge_documents"
    headers = {
        "Content-Type": "application/json",
        "API-Key": os.getenv("DOCUMENT_AGENT_API_KEY")
    }
    # Data payload for the POST request, including absolute path for server access
    data = {
        "input_dir": str(Path(input_dir).absolute()),
        "output_file": output_file,
        "context_docs": context_docs
    }

    try:
        # Add detailed tracing for each file being parsed
        print("Scanning input directory for documents to parse")
        for filename in os.listdir(input_dir):
            file_path = os.path.join(input_dir, filename)
            if os.path.isfile(file_path):
                print(f"Found document to parse: {filename}")

        # Send the request to the MCP Agent server
        print(f"Merging documents from: {input_dir}")
        print(f"Using context from: {', '.join(context_docs)}")
        response = requests.post(url, headers=headers, json=data)
        
        # Check the response status code to determine success or failure
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print("Documents merged successfully!")
                print("Details:", json.dumps(result, indent=2))
            else:
                print("Error merging documents:", result.get("message", "Unknown error"))
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        # Handle case where server is not running or inaccessible
        print("Error: Could not connect to the MCP Agent. Make sure it's running on port 8000.")
    except Exception as e:
        # Catch any other unexpected errors during the request
        print(f"Error: {str(e)}")

    print(f"Completed document merge process, output saved to: {output_file}")

if __name__ == "__main__":
    print("Entering main execution block")
    # Main execution block to set up paths and initiate document merging
    # Get the current directory where the script is located
    current_dir = Path(__file__).parent
    
    # Define the path to the documents directory for input files
    input_dir = current_dir / "documents"
    # Specify the name of the output merged document
    output_file = "merged_document.docx"
    
    # Automatically gather all document files in the input_dir as context documents
    context_docs = [f.name for f in Path(input_dir).iterdir() if f.is_file() and not f.name.startswith('.')]
    
    # Call the merge_documents function to start the merging process
    print("Calling document merge functionality")
    merge_documents(input_dir, output_file, context_docs)
    print("Merge process completed, output saved")
    print("Exiting main execution block")