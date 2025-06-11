import requests
import json
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables (e.g., API key) from .env file
load_dotenv()

# Initial log to indicate script execution has started
print("Starting merge_documents.py execution")

def process_document_pair(input_dir: str, doc_pair: List[str], pair_index: int) -> Dict:
    """Process a pair of documents and get their detailed summary."""
    print(f"\nProcessing document pair {pair_index + 1}:")
    print(f"Documents: {', '.join(doc_pair)}")
    
    url = "http://127.0.0.1:8000/tools/merge_documents"
    headers = {
        "Content-Type": "application/json",
        "API-Key": os.getenv("DOCUMENT_AGENT_API_KEY")
    }

    # Add detailed summary request in the data
    data = {
        "input_dir": str(Path(input_dir).absolute()),
        "output_file": f"pair_{pair_index + 1}_summary.docx",
        "document_sets": [
            {
                "name": f"Document Pair {pair_index + 1}",
                "documents": doc_pair,
                "summary_type": "detailed",  # Request detailed summary
                "include_sections": [
                    "main_points",
                    "key_findings",
                    "important_context",
                    "critical_information",
                    "recommendations",
                    "action_items"
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print(f"Successfully processed pair {pair_index + 1}")
                return result
            else:
                print(f"Error processing pair {pair_index + 1}:", result.get("message", "Unknown error"))
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the MCP Agent. Make sure it's running on port 8000.")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return None

def combine_summaries(summaries: List[Dict], output_file: str) -> None:
    """Combine all pair summaries into a final document with comprehensive analysis."""
    print("\nCombining all summaries into final document...")
    
    url = "http://127.0.0.1:8000/tools/merge_documents"
    headers = {
        "Content-Type": "application/json",
        "API-Key": os.getenv("DOCUMENT_AGENT_API_KEY")
    }
    
    # Create a document set for the summary documents
    summary_docs = [f"pair_{i+1}_summary.docx" for i in range(len(summaries))]
    
    data = {
        "input_dir": str(Path("output").absolute()),
        "output_file": output_file,
        "document_sets": [
            {
                "name": "Comprehensive Document Analysis",
                "documents": summary_docs,
                "summary_type": "comprehensive",  # Request comprehensive analysis
                "include_sections": [
                    "executive_summary",
                    "detailed_analysis",
                    "key_findings",
                    "important_context",
                    "critical_information",
                    "recommendations",
                    "action_items",
                    "cross_references",
                    "synthesis"
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print("Successfully combined all summaries!")
                print("Final document saved as:", output_file)
                
                # Clean up intermediate summary files
                output_dir = Path("output")
                for doc in summary_docs:
                    try:
                        (output_dir / doc).unlink()
                        print(f"Cleaned up intermediate file: {doc}")
                    except Exception as e:
                        print(f"Warning: Could not delete {doc}: {str(e)}")
            else:
                print("Error combining summaries:", result.get("message", "Unknown error"))
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
    except requests.exceptions.ConnectionError:   
        print("Error: Could not connect to the MCP Agent. Make sure it's running on port 8000.")
    except Exception as e:
        print(f"Error: {str(e)}")

def merge_documents(input_dir: str, output_file: str) -> None:
    print(f"Starting document merge process with input directory: {input_dir}")
    
    if not Path(input_dir).exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Get all documents from the input directory
    all_docs = [f.name for f in Path(input_dir).iterdir() if f.is_file() and not f.name.startswith('.')]
    
    if not all_docs:
        print("No documents found in the input directory.")
        return
    
    print(f"Found {len(all_docs)} documents to process")
    
    # Process documents in pairs
    pair_summaries = []
    i = 0
    
    # Process documents in pairs until we have 3 or fewer documents left
    while i < len(all_docs) - 3:
        pair = all_docs[i:i+2]  # Get next pair of documents
        print(f"\nProcessing pair {len(pair_summaries) + 1} (2 documents)")
        summary = process_document_pair(input_dir, pair, len(pair_summaries))
        if summary:
            pair_summaries.append(summary)
        i += 2
    
    # Handle the remaining documents
    remaining_docs = all_docs[i:]
    if remaining_docs:
        print(f"\nProcessing final set ({len(remaining_docs)} documents)")
        if len(remaining_docs) == 3:
            # Process last 3 documents together
            summary = process_document_pair(input_dir, remaining_docs, len(pair_summaries))
            if summary:
                pair_summaries.append(summary)
        else:
            # Process remaining documents in pairs
            for j in range(0, len(remaining_docs), 2):
                pair = remaining_docs[j:j+2]
                summary = process_document_pair(input_dir, pair, len(pair_summaries))
                if summary:
                    pair_summaries.append(summary)
    
    # Combine all summaries into final document
    if pair_summaries:
        combine_summaries(pair_summaries, output_file)
    else:
        print("No summaries were generated. Check the errors above.")

if __name__ == "__main__":
    print("Entering main execution block")

    # Determine the directory where the script is located
    current_dir = Path(__file__).parent

    # Set path to input documents directory
    input_dir = current_dir / "documents"

    # Name of the final merged output file
    output_file = "final_merged_document.docx"

    # Trigger the document merge process
    print("Calling document merge functionality")
    merge_documents(input_dir, output_file)

    # Final confirmation logs
    print("Merge process completed")
    print("Exiting main execution block")
