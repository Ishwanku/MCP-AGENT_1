# MCP Document Merge Agent

A Python-based document processing and merging tool that uses AI (Azure OpenAI) to analyze and combine multiple documents into structured summaries. The system supports parallel processing, robust error handling, and exposes a FastAPI server for API-based document operations.

## Features

- **Parallel Document Processing:**  
  Processes multiple document sets in parallel for efficiency.
- **AI-Powered Summarization:**  
  Integrates with Azure OpenAI for document analysis and summary generation.
- **API Endpoints:**  
  Exposes endpoints for merging documents and LLM-based content generation.
- **Configurable Output:**  
  Supports custom output styles, section-based organization, and professional formatting.
- **Robust Error Handling:**  
  Handles missing files, API failures, and formatting issues gracefully.

## Project Structure

```text
mcp-agent/
├── src/
│   ├── mcp/
│   │   ├── agents/
│   │   │   └── document_merge_agent.py
│   │   └── core/
│   │       ├── server.py
│   │       ├── document_parser.py
│   │       ├── llm_client.py
│   │       ├── config.py
|   |       ├── search_client.py
│   │       └── utils.py
│   ├── document_processor.py
|   └── run.py
├── documents/
├── output/
├── .env
├── pyproject.toml
├── setup.ps1
└── README.md
```

## Setup

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd mcp-agent
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/Mac:
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**  
   Create a `.env` file with your API keys and settings:

   ```env
   DOCUMENT_AGENT_API_KEY=your_api_key_here
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
   AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
   ```

## Usage

1. **Start the API server:**

   ```bash
   python src/mcp/agents/document_merge_agent.py
   ```

   or, if using the modular server:

   ```bash
   python src/mcp/core/server.py
   ```

2. **Place your documents in the `documents/` folder, organized by section:**

   ```text
   documents/
   ├── Section1/
   │   ├── doc1.docx
   │   └── doc2.docx
   ├── Section2/
   |   ├── doc3.docx
   │   └── doc4.docx
   ├── Section2/
   |   ├── doc5.docx
   │   └── doc6.docx
   ```

3. **Call the API endpoints:**  
   - `POST /tools/merge_documents` — Merge and summarize documents.
   - `POST /tools/llm` — Generate content using LLM.
   - `GET /` — Health check.

   Use tools like `curl`, Postman, or your own client to interact with the API.

4. **Output:**  
   Merged and summarized documents are saved in the `output/` directory.

## API Example

- **Merge Documents:**

  ```json
  POST /tools/merge_documents
  Headers: { "API-Key": "<your_api_key>" }
  Body:
  {
    "input_dir": "documents/Section1",
    "output_file": "output/merged.docx",
    "document_sets": [
      {
        "name": "Section1",
        "documents": ["doc1.docx", "doc2.docx"],
        "summary_type": "executive",
        "include_sections": ["all"]
      }
    ]
  }
  ```

## Error Handling

- Handles missing documents, API failures, and formatting errors.
- Returns clear error messages and status codes.
