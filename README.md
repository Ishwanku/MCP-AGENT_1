# MCP Document Merge Agent

A powerful document processing and merging tool that combines multiple documents into a single, well-structured Word document. It uses Google's Gemini AI for intelligent document analysis and summarization.

## Features

- **Document Merging**: Combines multiple documents into a single Word document
- **Intelligent Analysis**: Uses Gemini AI to analyze and understand document content
- **Structured Output**: Creates well-formatted documents with proper styling and organization
- **Context Preservation**: Maintains important formatting and structure from source documents

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mcp-agent.git
cd mcp-agent
```

2. Install dependencies:
```bash
pip install -e .
```

3. Create a `.env` file in the project root with your API key:
```env
DOCUMENT_AGENT_API_KEY=your_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

1. Start the server:
```bash
python run.py
```

2. Use the merge_documents.py script to process documents:
```bash
python merge_documents.py
```

## Configuration

The following environment variables can be configured in the `.env` file:

- `DOCUMENT_AGENT_API_KEY`: API key for the document agent
- `GEMINI_API_KEY`: API key for Gemini AI

## Project Structure

- `mcp/core/`: Core functionality
  - `document_parser.py`: Document processing and merging
  - `llm_client.py`: Gemini AI integration
  - `config.py`: Configuration settings

- `merge_documents.py`: Main script for document processing
- `run.py`: Server startup script

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
