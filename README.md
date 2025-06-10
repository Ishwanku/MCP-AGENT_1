# MCP Document Merge Agent

## Overview

The MCP Document Merge Agent is a Python-based tool designed to merge multiple document types (DOCX, PDF, TXT, PPTX) into a single Word document. Built on FastAPI, it provides a server-client architecture for seamless document processing with optional summarization using configurable Large Language Model (LLM) providers such as Ollama, OpenAI, and Gemini.

### Key Features

- **Multi-Format Support**: Merges DOCX, PDF, TXT, and PPTX files into a unified Word document while preserving structure where possible.
- **LLM Summarization**: Optionally summarizes or extracts context from documents using Ollama (local), OpenAI, or Gemini.
- **RESTful API**: Provides a secure HTTP endpoint for document merging, accessible via client scripts or external applications.
- **Configurable Providers**: Switch between LLM providers via environment variables without code changes.
- **Detailed Logging**: Offers comprehensive logs for debugging and monitoring server operations.

## Installation

### Prerequisites

- **Python 3.10+**: Ensure Python is installed on your system.
- **Virtual Environment**: Recommended for dependency isolation.
- **Git**: For cloning the repository (optional).

### Setup Steps

1. **Clone the Repository** (if applicable):

   ```bash
   git clone <repository-url>
   cd mcp-agent
   ```

2. **Create and Activate Virtual Environment**:
   - Windows:

     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```

   - Linux/macOS:

     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies**:
   Run the setup script to install required packages:

   ```bash
   powershell -ExecutionPolicy Bypass -File ./setup.ps1  # Windows
   # OR
   python run.py  # This will also install dependencies before starting the server
   ```

   If the setup script fails with errors about 'all' extras, it will fall back to installing individual dependencies for LLM providers.

4. **Configure Environment Variables**:
   Create a `.env` file in the project root with necessary settings (copy from `.env.example` if available):

   ```plaintext
   DOCUMENT_AGENT_PORT=8000
   LLM_PROVIDER=ollama  # Options: ollama, openai, gemini
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### Starting the Server

Run the server to handle document merge requests:

```bash
python run.py
```

The server will start on the configured port (default: 8000), and you'll see logs indicating it's running at `http://0.0.0.0:8000`.

### Merging Documents

Use the client script to merge documents from the default `documents/` directory:

```bash
python merge_documents.py
```

- The script scans the `documents/` folder for files to merge.
- Output is saved to `output/merged_document.docx` by default.
- Check the terminal for status messages and any errors.

### API Interaction

You can interact with the API directly using tools like `curl` or Postman:

- Endpoint: `http://localhost:8000/tools/merge_documents`
- Method: POST
- Headers: `Content-Type: application/json`, `API-Key: your_api_key_here` (if configured)
- Body:

  ```json
  {
    "input_dir": "path/to/your/documents",
    "output_file": "merged_document.docx",
    "context_docs": ["doc1.pdf", "doc2.docx"]
  }
  ```

## Configuration

Settings are managed via environment variables or a `.env` file:

- `DOCUMENT_AGENT_PORT`: Port for the server (default: 8000).
- `LLM_PROVIDER`: LLM for summarization (ollama, openai, gemini).
- `GEMINI_API_KEY`, `OPENAI_API_KEY`: API keys for respective providers.
- `OUTPUT_DIR`: Directory for merged files (default: output/).

## Troubleshooting

- **Server Fails to Start**: Check if the port (default: 8000) is in use. Change `DOCUMENT_AGENT_PORT` in `.env` if needed.
- **Gemini API Issues**: If you see 'Gemini client not available' or quota errors, verify your `GEMINI_API_KEY` in `.env`. Check Google's API console for quota limits or registration issues. The application falls back to direct HTTP requests if library authentication fails.
- **Dependency Errors**: Ensure all packages are installed (`pip install -e .[all]` or via `setup.ps1`). If 'all' extra fails, dependencies are installed individually.
- **Context Extraction Unavailable**: If summarization fails, ensure the LLM provider is correctly configured with a valid API key or local setup (for Ollama).

## Project Structure and Code Documentation

Below is an overview of the project's file structure and detailed documentation for each key code file:

- **`run.py`**: Entry point to start the FastAPI server.
  - **Purpose**: Serves as the main script to configure the environment, install dependencies, and launch the server.
  - **Key Functions**:
    - `check_python_version()`: Ensures Python version compatibility (3.9+).
    - `create_venv()`: Creates a virtual environment if it doesn't exist.
    - `install_dependencies()`: Installs required packages and optional LLM dependencies.
    - `start_agent()`: Launches the FastAPI server using Uvicorn.
    - `main()`: Orchestrates the setup and server startup process.
  - **Usage**: Run with `python run.py` to start the server.

- **`merge_documents.py`**: Client script to interact with the API for merging documents.
  - **Purpose**: Sends HTTP requests to the server to merge documents from a specified directory.
  - **Key Functions**:
    - `merge_documents(input_dir, output_file, context_docs)`: Prepares and sends a POST request to the merge endpoint, handling responses and errors.
  - **Usage**: Run with `python merge_documents.py` to merge documents from the default `documents/` folder.

- **`mcp/core/config.py`**: Configuration settings loaded from environment variables.
  - **Purpose**: Manages application settings using Pydantic's `BaseSettings` for type safety and validation.
  - **Key Attributes**:
    - `DOCUMENT_AGENT_PORT`: Server port (default: 8000).
    - `LLM_PROVIDER`: Specifies the LLM provider (default: ollama).
    - `OPENAI_API_KEY`, `GEMINI_API_KEY`: API keys for respective providers.
    - `OUTPUT_DIR`: Directory for output files.
  - **Usage**: Settings are automatically loaded from `.env` or environment variables and used throughout the application.

- **`mcp/core/llm_client.py`**: Unified interface for LLM providers (Ollama, OpenAI, Gemini).
  - **Purpose**: Abstracts interactions with different LLM providers behind a single client interface for summarization tasks.
  - **Key Class**: `LLMClient`
    - `__init__()`: Initializes the client based on the configured provider and API keys.
    - `summarize_text(text, max_length)`: Summarizes text using the selected provider.
    - `is_available()`: Checks if the LLM provider is available.
    - `generate_content(prompt)`: Generates content based on a given prompt.
  - **Usage**: Instantiated once and used for all summarization tasks in the application.

- **`mcp/core/document_parser.py`**: Handles parsing and merging of various document formats.
  - **Purpose**: Parses DOCX, PDF, TXT, and PPTX files into a single Word document, with optional LLM summarization.
  - **Key Class**: `DocumentParser`
    - `__init__()`: Initializes supported file extensions and their parsing methods.
    - `create_context_document(context_files, output_file)`: Merges documents into a Word file with extracted context.
    - `_parse_txt()`, `_parse_pdf()`, `_parse_docx()`, `_parse_pptx()`: Specific parsing methods for each file type.
    - `summarize_text(text, max_length)`: Uses LLM to summarize content.
    - `_init_document_styles(doc)`: Ensures consistent styling in the output document.
  - **Usage**: Used by the server to process merge requests.

- **`mcp/core/server.py`**: Server utilities and FastAPI-based MCP server implementation.
  - **Purpose**: Provides the core server functionality for tool registration and API endpoints.
  - **Key Class**: `FastMCP`
    - `__init__(name, port, api_key)`: Initializes the server with a name, port, and optional API key.
    - `register_tool(name, func)`: Registers tools for API access.
    - `run()`: Starts the FastAPI server using Uvicorn.
  - **Usage**: Forms the basis for the document merge agent's server setup.

- **`mcp/agents/document_merge_agent.py`**: Core FastAPI application for document merging.
  - **Purpose**: Defines the main API endpoints for document merging operations.
  - **Key Components**:
    - `MergeRequest`, `MergeResponse`: Pydantic models for request and response structures.
    - `/tools/merge_documents` Endpoint: Handles document merge requests with API key validation.
  - **Usage**: Launched via `run.py` to start the server and handle HTTP requests.
