"""
Document Parser for MCP Document Merge Agent

This module handles the parsing and merging of various document types (DOCX, PDF, TXT, PPTX)
into a single Word document for the MCP Document Merge Agent. It integrates with LLM clients
for optional summarization or context extraction to enhance the merged output.

Key Features:
- Supports multiple document formats through specialized parsing methods.
- Merges content into a unified Word document while preserving structure where possible.
- Optionally uses LLM providers to summarize or extract context from documents.
- Provides detailed logging for parsing and merging operations.

Usage:
    The DocumentParser class is instantiated and used by the FastAPI application to process
    document merge requests. It scans input directories for supported files, parses their content,
    optionally summarizes using an LLM, and generates a merged DOCX file.

Configuration:
    Relies on settings from `config.py` for output directory (OUTPUT_DIR) and LLM integration
    via the `llm_client` module. No direct configuration is required within this module.

Dependencies:
    Requires external libraries like `pdf2docx` for PDF conversion, `python-docx` for DOCX handling,
    and `pptx` for PowerPoint files. These are installed as part of the project dependencies.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import PyPDF2
from PIL import Image
import io
from pptx import Presentation

# Attempt to import Ollama client for local LLM summarization
try:
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Ollama client not available. Summarization with Ollama will be disabled.")

# Attempt to import OpenAI client for cloud-based summarization
try:
    from openai import OpenAI as OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI client not available. Summarization with OpenAI will be disabled.")

# Attempt to import Gemini client for Google's AI summarization
try:
    from google.generativeai import GenerativeModel as GeminiClient
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Gemini client not available. Summarization with Gemini will be disabled.")

# Import configuration settings and LLM client for summarization
from .config import Settings
from .llm_client import llm_client

# Initialize settings to access LLM configuration
settings = Settings()

class DocumentParser:
    """
    A class to parse various document types into a Word document format with consistent styling
    and source context preservation.

    This class handles the parsing of multiple document formats (.docx, .txt, .pdf, .pptx) and
    merges them into a single Word document. It maintains formatting and styles where possible
    and adds source context to identify the origin of content in the merged output.

    Attributes:
        supported_extensions (dict): A mapping of file extensions to their respective parsing methods.
        style_mapping (dict): A dictionary for tracking style mappings between source and target documents.

    Methods:
        create_context_document(context_files, output_file):
            Merges multiple input documents into a single Word document with styling and context.
        _init_document_styles(doc):
            Initializes standard styles in a Word document for consistent formatting.
        _get_safe_style(doc, style_name):
            Retrieves a safe, existing style name from a document to avoid formatting errors.
        _add_source_heading(doc, file_path, source_type):
            Adds a heading to indicate the source of content in the merged document.
        _parse_txt(file_path):
            Parses a plain text file into a Word document.
        _parse_pdf(file_path):
            Parses a PDF file into a Word document with advanced formatting preservation.
        _parse_docx(file_path):
            Parses a Word document, copying content, styles, tables, and images.
        _parse_pptx(file_path):
            Parses a PowerPoint file into a Word document.
        summarize_text(text: str, max_length: int = 200) -> str:
            Summarizes the given text using the configured LLM provider.
    """
    
    def __init__(self):
        """
        Initialize the DocumentParser with supported file extensions and their parsing handlers.
        
        Sets up a dictionary mapping file extensions to their respective parsing methods for
        dynamic parser selection based on file type. Also initializes a style mapping dictionary
        to track style correspondences between source and target documents. Configures LLM clients
        based on availability and settings.
        """
        self.supported_extensions = {
            '.txt': self._parse_txt,
            '.pdf': self._parse_pdf,
            '.docx': self._parse_docx,
            '.pptx': self._parse_pptx
        }
        self.style_mapping = {}  # For tracking style mappings between documents
        self.settings = Settings()
        self.llm = llm_client
        if OLLAMA_AVAILABLE and self.settings.LLM_PROVIDER == "ollama":
            self.ollama_client = OllamaClient(host='localhost:11434')
        else:
            self.ollama_client = None
        if OPENAI_AVAILABLE and self.settings.LLM_PROVIDER == "openai" and self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAIClient(api_key=self.settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
        if GEMINI_AVAILABLE and self.settings.LLM_PROVIDER == "gemini" and self.settings.GEMINI_API_KEY:
            genai.configure(api_key=self.settings.GEMINI_API_KEY)
            self.gemini_client = GeminiClient(self.settings.GEMINI_MODEL)
        else:
            self.gemini_client = None
    
    def _init_document_styles(self, doc: docx.Document) -> None:
        """
        Initialize standard document styles for consistent formatting across merged content.

        Sets up predefined styles for normal text, headings (levels 1 to 3), and tables in the
        provided Word document if they do not already exist, ensuring uniformity in the appearance
        of the merged document.

        Args:
            doc (docx.Document): The Word document object to initialize styles for.
        """
        styles = doc.styles

        # Normal style for regular text content
        if 'Normal' not in styles:
            normal_style = styles.add_style('Normal', WD_STYLE_TYPE.PARAGRAPH)
            normal_style.font.name = 'Calibri'
            normal_style.font.size = Pt(11)

        # Heading styles for document structure (levels 1 to 3)
        for i in range(1, 4):
            style_name = f'Heading {i}'
            if style_name not in styles:
                heading_style = styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                heading_style.font.name = 'Calibri'
                heading_style.font.size = Pt(14 - i)
                heading_style.font.bold = True

        # Table style for consistent table formatting
        if 'Table Grid' not in styles:
            table_style = styles.add_style('Table Grid', WD_STYLE_TYPE.TABLE)
            table_style.font.name = 'Calibri'
            table_style.font.size = Pt(10)

    def _get_safe_style(self, doc: docx.Document, style_name: str) -> str:
        """
        Retrieve a safe style name that exists in the document to prevent formatting errors.

        Checks if a given style name exists in the document. If it does not, attempts to find a
        normalized version by removing parenthetical content. Defaults to 'Normal' if no match is
        found, ensuring content can be formatted without exceptions.

        Args:
            doc (docx.Document): The document to check styles in.
            style_name (str): The original style name to verify.

        Returns:
            str: A safe style name that exists in the document.
        """
        # First try the exact style name as provided
        if style_name in doc.styles:
            return style_name
        
        # Try to normalize the style name by removing any parenthetical content
        normalized_name = style_name.split('(')[0].strip()
        if normalized_name in doc.styles:
            return normalized_name
        
        # If all else fails, return 'Normal' as a safe default
        return 'Normal'

    def _add_source_heading(self, doc: docx.Document, file_path: Path, source_type: str) -> None:
        """
        Add a heading to the document indicating the source of the content.

        Adds a heading to clearly identify the source document's name and type, aiding in context
        preservation within the merged document.

        Args:
            doc (docx.Document): The document to add the heading to.
            file_path (Path): Path to the source file for naming in the heading.
            source_type (str): Type of source document (e.g., "PDF", "Slide") for description.
        """
        heading = doc.add_paragraph()
        heading.style = self._get_safe_style(doc, 'Heading 1')
        heading.add_run(f"Document: {file_path.name} (Source: {source_type})")

    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Extract important context from the given text using the configured LLM provider.
        
        Delegates the summarization task to the LLM client, passing the text and desired length.
        
        Args:
            text (str): The text to analyze for important context.
            max_length (int): The approximate maximum length of the extracted context in words.
        
        Returns:
            str: The extracted context or a message indicating processing is unavailable.
        """
        return self.llm.summarize_text(text, max_length)

    def create_context_document(self, context_files: List[Path], output_file: str) -> docx.Document:
        """
        Create a Word document containing only the important context extracted from input documents.

        Orchestrates the process by creating a new Word document, initializing its styles,
        and adding extracted important context for each input document using a local LLM if available.
        Does not include the full content of the input documents.

        Args:
            context_files (List[Path]): List of input document paths to process for context extraction.
            output_file (str): Name of the output file (used for temporary saving during processing).

        Returns:
            docx.Document: The Word document object with extracted contexts, ready for final saving.
        """
        # Create a new empty Word document as the base for merging
        doc = docx.Document()
        self._init_document_styles(doc)
        
        # Add a title for the merged document
        title = doc.add_paragraph()
        title.style = self._get_safe_style(doc, 'Heading 1')
        title.add_run(f"Merged Document: {output_file}")
        
        # Add a context section at the top
        context_heading = doc.add_paragraph()
        context_heading.style = self._get_safe_style(doc, 'Heading 2')
        context_heading.add_run("Important Context from Documents")
        
        # Process each input document
        for i, file_path in enumerate(context_files, 1):
            print(f"Processing document {i}/{len(context_files)}: {file_path.name}")
            # Parse the document based on its extension
            try:
                temp_doc = self.supported_extensions[file_path.suffix.lower()](file_path)
                # Extract text for context extraction
                text_content = "\n".join([p.text for p in temp_doc.paragraphs])
                # Extract important context
                context = self.summarize_text(text_content)
                # Add context to the context section
                context_para = doc.add_paragraph()
                context_para.style = self._get_safe_style(doc, 'Heading 3')
                context_para.add_run(f"Context from {file_path.name}")
                doc.add_paragraph(context, style=self._get_safe_style(doc, 'Normal'))
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                error_para = doc.add_paragraph()
                error_para.style = self._get_safe_style(doc, 'Heading 3')
                error_para.add_run(f"Context from {file_path.name}")
                doc.add_paragraph(f"Could not extract context due to: {str(e)}", style=self._get_safe_style(doc, 'Normal'))
        
        return doc
    
    def _parse_txt(self, file_path: Path) -> docx.Document:
        """
        Parse a plain text file into a Word document format.

        Reads the content of a plain text file and creates a new Word document with the text
        formatted using the 'Normal' style. This method is used as part of the document merging
        process for .txt files.

        Args:
            file_path (Path): Path to the text file to be parsed.

        Returns:
            docx.Document: A Word document containing the parsed text content.
        """
        print(f"Entering _parse_txt for file: {file_path}")
        doc = docx.Document()
        self._init_document_styles(doc)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            paragraph = doc.add_paragraph()
            paragraph.style = self._get_safe_style(doc, 'Normal')
            paragraph.add_run(content)
        print(f"Exiting _parse_txt for file: {file_path}")
        return doc
    
    def _parse_pdf(self, file_path: Path) -> docx.Document:
        """
        Parse a PDF file into a Word document format.

        Converts a PDF file to a Word document using pdf2docx for better preservation of layout,
        tables, and formatting. If pdf2docx is not available, falls back to pdfplumber with
        enhanced text parsing for bullet points, headings, and bold text. As a last resort, uses
        PyPDF2 for basic text extraction.

        Args:
            file_path (Path): Path to the PDF file to be parsed.

        Returns:
            docx.Document: A Word document containing the parsed PDF content.
        """
        print(f"Entering _parse_pdf for file: {file_path}")
        doc = docx.Document()
        self._init_document_styles(doc)
        
        try:
            from pdf2docx import Converter
            # Create a temporary output file for the converted Word document
            temp_docx_path = Path('temp_pdf_conversion.docx')
            # Convert PDF to DOCX
            cv = Converter(str(file_path))
            cv.convert(str(temp_docx_path))
            cv.close()
            # Load the converted DOCX file
            converted_doc = docx.Document(str(temp_docx_path))
            # Copy content from converted DOCX to our document
            for para in converted_doc.paragraphs:
                new_para = doc.add_paragraph()
                new_para.style = self._get_safe_style(doc, para.style.name)
                for run in para.runs:
                    new_run = new_para.add_run(run.text)
                    new_run.bold = run.bold
                    new_run.italic = run.italic
                    new_run.underline = run.underline
            # Copy tables from converted DOCX
            for table in converted_doc.tables:
                new_table = doc.add_table(rows=len(table.rows), cols=len(table.columns))
                new_table.style = self._get_safe_style(doc, 'Table Grid')
                for i, row in enumerate(table.rows):
                    for j, cell in enumerate(row.cells):
                        new_cell = new_table.cell(i, j)
                        new_cell.paragraphs[0].style = self._get_safe_style(doc, 'Normal')
                        for para in cell.paragraphs:
                            new_para = new_cell.add_paragraph()
                            new_para.style = self._get_safe_style(doc, para.style.name)
                            for run in para.runs:
                                new_run = new_para.add_run(run.text)
                                new_run.bold = run.bold
                                new_run.italic = run.italic
                                new_run.underline = run.underline
            # Clean up temporary file
            if temp_docx_path.exists():
                temp_docx_path.unlink()
            print(f"Successfully converted PDF {file_path.name} to DOCX using pdf2docx")
        except ImportError:
            print(f"pdf2docx not installed, falling back to pdfplumber for {file_path.name}")
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        # Add page number as heading
                        heading = doc.add_paragraph()
                        heading.style = self._get_safe_style(doc, 'Heading 2')
                        heading.add_run(f"Page {page_num}")
                        
                        # Extract text and process line by line for formatting
                        text = page.extract_text()
                        if text:
                            lines = text.split('\n')
                            in_list = False
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                # Handle headings (e.g., ### Heading)
                                if line.startswith('### '):
                                    if in_list:
                                        in_list = False
                                    heading_para = doc.add_paragraph()
                                    heading_para.style = self._get_safe_style(doc, 'Heading 3')
                                    heading_para.add_run(line[4:].strip())
                                    continue
                                # Handle bold headings (e.g., **Heading:**)
                                if line.startswith('**') and line.endswith(':**'):
                                    if in_list:
                                        in_list = False
                                    heading_para = doc.add_paragraph()
                                    heading_para.style = self._get_safe_style(doc, 'Heading 3')
                                    heading_text = line[2:-3].strip()
                                    heading_para.add_run(heading_text).bold = True
                                    continue
                                # Handle bullet points (e.g., - Text or * Text)
                                if line.startswith('- ') or line.startswith('* '):
                                    if not in_list:
                                        in_list = True
                                    bullet_text = line[2:].strip()
                                    bullet_para = doc.add_paragraph()
                                    bullet_para.style = self._get_safe_style(doc, 'Normal')
                                    bullet_para.paragraph_format.left_indent = Inches(0.5)
                                    bullet_para.paragraph_format.first_line_indent = Inches(-0.25)
                                    # Check for bold within bullet (e.g., **bold**)
                                    if '**' in bullet_text:
                                        parts = bullet_text.split('**')
                                        for i, part in enumerate(parts):
                                            if i % 2 == 1:  # Bold part
                                                bullet_para.add_run(part).bold = True
                                            else:
                                                bullet_para.add_run(part)
                                    else:
                                        bullet_para.add_run(bullet_text)
                                    continue
                                # Handle normal text
                                if in_list:
                                    in_list = False
                                normal_para = doc.add_paragraph()
                                normal_para.style = self._get_safe_style(doc, 'Normal')
                                # Check for bold text (e.g., **bold**)
                                if '**' in line:
                                    parts = line.split('**')
                                    for i, part in enumerate(parts):
                                        if i % 2 == 1:  # Bold part
                                            normal_para.add_run(part).bold = True
                                        else:
                                            normal_para.add_run(part)
                                else:
                                    normal_para.add_run(line)
                        
                        # Extract tables if any
                        tables = page.extract_tables()
                        if tables:
                            print(f"Found {len(tables)} table(s) on page {page_num} of {file_path.name}")
                        for table_idx, table_data in enumerate(tables):
                            if table_data:
                                # Create a table in the Word document
                                rows = len(table_data)
                                cols = max(len(row) for row in table_data if row) if table_data else 0
                                if rows > 0 and cols > 0:
                                    print(f"Processing table {table_idx+1} on page {page_num}: {rows} rows, {cols} columns")
                                    new_table = doc.add_table(rows=rows, cols=cols)
                                    new_table.style = self._get_safe_style(doc, 'Table Grid')
                                    for i, row in enumerate(table_data):
                                        for j, cell_text in enumerate(row if row else []):
                                            if cell_text and i < rows and j < cols:
                                                cell = new_table.cell(i, j)
                                                cell.text = str(cell_text).strip()
                                                cell.paragraphs[0].style = self._get_safe_style(doc, 'Normal')
                                                print(f"Cell ({i},{j}) content: {str(cell_text).strip()[:50]}...")
            except ImportError:
                # Fallback to PyPDF2 if pdfplumber is also not installed
                print(f"pdfplumber not installed, falling back to PyPDF2 for {file_path.name}")
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        # Add page number as heading
                        heading = doc.add_paragraph()
                        heading.style = self._get_safe_style(doc, 'Heading 2')
                        heading.add_run(f"Page {page_num}")
                        
                        # Add content with basic formatting detection
                        text = page.extract_text()
                        if text:
                            lines = text.split('\n')
                            in_list = False
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                # Handle headings (e.g., ### Heading)
                                if line.startswith('### '):
                                    if in_list:
                                        in_list = False
                                    heading_para = doc.add_paragraph()
                                    heading_para.style = self._get_safe_style(doc, 'Heading 3')
                                    heading_para.add_run(line[4:].strip())
                                    continue
                                # Handle bold headings (e.g., **Heading:**)
                                if line.startswith('**') and line.endswith(':**'):
                                    if in_list:
                                        in_list = False
                                    heading_para = doc.add_paragraph()
                                    heading_para.style = self._get_safe_style(doc, 'Heading 3')
                                    heading_text = line[2:-3].strip()
                                    heading_para.add_run(heading_text).bold = True
                                    continue
                                # Handle bullet points (e.g., - Text or * Text)
                                if line.startswith('- ') or line.startswith('* '):
                                    if not in_list:
                                        in_list = True
                                    bullet_text = line[2:].strip()
                                    bullet_para = doc.add_paragraph()
                                    bullet_para.style = self._get_safe_style(doc, 'Normal')
                                    bullet_para.paragraph_format.left_indent = Inches(0.5)
                                    bullet_para.paragraph_format.first_line_indent = Inches(-0.25)
                                    # Check for bold within bullet (e.g., **bold**)
                                    if '**' in bullet_text:
                                        parts = bullet_text.split('**')
                                        for i, part in enumerate(parts):
                                            if i % 2 == 1:  # Bold part
                                                bullet_para.add_run(part).bold = True
                                            else:
                                                bullet_para.add_run(part)
                                    else:
                                        bullet_para.add_run(bullet_text)
                                    continue
                                # Handle normal text
                                if in_list:
                                    in_list = False
                                normal_para = doc.add_paragraph()
                                normal_para.style = self._get_safe_style(doc, 'Normal')
                                # Check for bold text (e.g., **bold**)
                                if '**' in line:
                                    parts = line.split('**')
                                    for i, part in enumerate(parts):
                                        if i % 2 == 1:  # Bold part
                                            normal_para.add_run(part).bold = True
                                        else:
                                            normal_para.add_run(part)
                                else:
                                    normal_para.add_run(line)
        print(f"Exiting _parse_pdf for file: {file_path}")
        return doc
    
    def _parse_docx(self, file_path: Path) -> docx.Document:
        """
        Parse a Word document into a Word document format, preserving content and formatting.

        Loads a Word document and copies its content, including paragraphs, styles, tables, and
        images, into a new Word document with initialized styles. This method ensures that the
        original formatting is maintained as much as possible during the merge process.

        Args:
            file_path (Path): Path to the Word document to be parsed.

        Returns:
            docx.Document: A new Word document containing the parsed content.
        """
        print(f"Entering _parse_docx for file: {file_path}")
        source_doc = docx.Document(file_path)
        doc = docx.Document()
        self._init_document_styles(doc)
        
        # Map source styles to target styles
        for style in source_doc.styles:
            if style.name not in self.style_mapping:
                self.style_mapping[style.name] = self._get_safe_style(doc, style.name)
        
        # Copy paragraphs with style mapping
        for para in source_doc.paragraphs:
            new_para = doc.add_paragraph()
            new_para.style = self._get_safe_style(doc, para.style.name)
            for run in para.runs:
                new_run = new_para.add_run(run.text)
                new_run.bold = run.bold
                new_run.italic = run.italic
                new_run.underline = run.underline
        
        # Copy tables with style mapping
        for table in source_doc.tables:
            new_table = doc.add_table(rows=len(table.rows), cols=len(table.columns))
            new_table.style = self._get_safe_style(doc, 'Table Grid')
            
            for i, row in enumerate(table.rows):
                for j, cell in enumerate(row.cells):
                    new_cell = new_table.cell(i, j)
                    # Set style for default paragraph in the cell
                    new_cell.paragraphs[0].style = self._get_safe_style(doc, 'Normal')
                    for para in cell.paragraphs:
                        new_para = new_cell.add_paragraph()
                        new_para.style = self._get_safe_style(doc, para.style.name)
                        for run in para.runs:
                            new_run = new_para.add_run(run.text)
                            new_run.bold = run.bold
                            new_run.italic = run.italic
                            new_run.underline = run.underline
        
        # Copy images
        for rel in source_doc.part.rels.values():
            if "image" in rel.target_ref:
                image_data = rel.target_part.blob
                doc.add_picture(io.BytesIO(image_data), width=Inches(6))
        
        print(f"Exiting _parse_docx for file: {file_path}")
        return doc
    
    def _parse_pptx(self, file_path: Path) -> docx.Document:
        """
        Parse a PowerPoint file into a Word document format.

        Extracts text and images from a PowerPoint presentation and converts them into a Word
        document. Each slide's content is separated by a heading indicating the slide number,
        and text is formatted using the 'Normal' style.

        Args:
            file_path (Path): Path to the PowerPoint file to be parsed.

        Returns:
            docx.Document: A Word document containing the parsed PowerPoint content.
        """
        doc = docx.Document()
        self._init_document_styles(doc)
        
        prs = Presentation(file_path)
        for slide_num, slide in enumerate(prs.slides, 1):
            # Add slide number as heading
            heading = doc.add_paragraph()
            heading.style = self._get_safe_style(doc, 'Heading 2')
            heading.add_run(f"Slide {slide_num}")
            
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    paragraph = doc.add_paragraph()
                    paragraph.style = self._get_safe_style(doc, 'Normal')
                    paragraph.add_run(shape.text)
                
                # Handle images
                if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                    try:
                        image_stream = shape.image.blob
                        doc.add_picture(io.BytesIO(image_stream), width=Inches(6))
                    except Exception as e:
                        print(f"Error processing image in slide {slide_num}: {e}")
        
        return doc