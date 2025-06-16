# MCP Document Merge Agent

A Python-based document processing and merging tool that uses AI to analyze and combine multiple documents into a comprehensive summary. The tool processes documents in parallel using LangGraph and provides structured output with consistent formatting.

## Features

- **Parallel Document Processing**
  - Processes multiple folders simultaneously
  - Handles multiple documents per folder
  - Uses LangGraph for workflow management
  - Automatic section numbering and organization

- **AI-Powered Analysis**
  - Azure OpenAI integration for document analysis
  - Retry mechanism for robust LLM calls
  - Structured output with consistent formatting
  - Comprehensive document summaries

- **Document Organization**
  - Section-based organization
  - Automatic section numbering
  - Consistent heading styles and colors
  - Configurable document styles

- **Output Format**
  The merged document includes:
  - Main Points
  - Document Summaries
  - Key Findings
  - Important Information
  - Cross-references between documents

- **Styling Features**
  - Configurable document styles
  - Consistent formatting throughout
  - Customizable fonts, colors, and spacing
  - Professional document layout

## Prerequisites

- Python 3.9 or higher
- Azure OpenAI API access
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd mcp-agent
```

2.Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3.Install dependencies:

```bash
pip install -r requirements.txt
```

4.Set up environment variables:

```bash
# Required settings
DOCUMENT_AGENT_API_KEY=your_api_key_here
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Optional settings (if you want to override defaults)
HOST=0.0.0.0
PORT=8000
DOCUMENT_AGENT_PORT=8000
OUTPUT_DIR=output
API_BASE_URL=http://127.0.0.1:8000

# Optional Azure Search settings (if using search functionality)
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your_search_service_key
AZURE_SEARCH_INDEX_NAME=documents

# Optional Content Safety settings
CONTENT_SAFETY_ENABLED=true
CONTENT_SAFETY_THRESHOLD=0.7

# Optional LLM settings
LLM_DEFAULT_MAX_TOKENS=1000
LLM_DEFAULT_TEMPERATURE=0.7
```

## Usage

1. Place your documents in the `documents` folder, organized by sections:

``
documents/
├── Section1/
│   ├── document1.docx
│   └── document2.docx
├── Section2/
│   ├── document3.docx
│   └── document4.docx
└── Section3/
    ├── document5.docx
    └── document6.docx
``

2.Run the document processor:

```bash
python src/parallel_document_processor.py
```

3.The merged document will be created in the `output` folder with a timestamp.

## Project Structure

``
mcp-agent/
├── src/
│   ├── mcp/
│   │   ├── agents/
│   │   │   └── document_merge_agent.py
│   │   └── core/
│   │       ├── document_parser.py
│   │       ├── llm_client.py
│   │       ├── config.py
│   │       └── utils.py
│   └── parallel_document_processor.py
├── documents/
│   ├── Section1/
│   ├── Section2/
│   └── Section3/
├── output/
├── .env
└── requirements.txt
``

## Configuration

The project uses a hierarchical configuration system:

1. **Environment Variables**
   - Loaded from `.env` file
   - Can override default settings
   - Required for API keys and endpoints

2. **Document Styles**
   - Configurable through settings
   - Default styles for different heading levels
   - Customizable fonts, colors, and spacing

3. **LLM Settings**
   - Configurable token limits
   - Adjustable temperature
   - Retry mechanisms

## API Endpoints

The service provides the following endpoints:

- `POST /tools/merge_documents`: Merge multiple documents
- `POST /tools/llm`: Generate content using LLM
- `GET /`: Health check endpoint

## Error Handling

The system includes comprehensive error handling for:

- Missing documents
- API failures
- LLM processing errors
- Document formatting issues
- Configuration validation

## Retry Mechanism

The system implements a robust retry mechanism for LLM calls:

- Maximum 3 retry attempts
- Exponential backoff
- Detailed error logging
- Exception handling
