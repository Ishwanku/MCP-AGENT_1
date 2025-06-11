import json
import re
from pathlib import Path
from typing import Dict, List, Any
import docx
from docx.shared import Pt, RGBColor
from .llm_client import LLMClient
from .config import Settings

# Document parser class to process, analyze and summarize
class DocumentParser:

    # If user give the llm_client then it uses that if not given then it makes default LLMClient by using setting() 
    def __init__(self, llm_client: LLMClient = None):
        """Initialize the DocumentParser with an optional LLMClient."""
        self.llm_client = llm_client or LLMClient(Settings())
    
    def _set_style_properties(self, style, font_name: str = 'Arial', size: int = 11, bold: bool = False):
        """Set common style properties for a given style."""
        style.font.name = font_name
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.color.rgb = RGBColor(0, 0, 0)
    
    def _init_document_styles(self, doc: docx.Document):
        """Initialize document styles for consistent formatting."""
        styles = doc.styles
        self._set_style_properties(styles['Title'], size=24, bold=True)
        self._set_style_properties(styles['Heading 1'], size=18, bold=True)
        self._set_style_properties(styles['Heading 2'], size=16, bold=True)
        self._set_style_properties(styles['Heading 3'], size=14, bold=True)
        self._set_style_properties(styles['Normal'], size=11)
    
    def _get_safe_style(self, doc: docx.Document, style_name: str) -> docx.styles.style._ParagraphStyle:
        """Get a style from the document, falling back to 'Normal' if not found."""
        try:
            return doc.styles[style_name]
        except KeyError:
            return doc.styles['Normal']
    
    def _add_styled_paragraph(self, doc: docx.Document, text: str, style_name: str) -> docx.text.paragraph.Paragraph:
        """Add a styled paragraph to the document."""
        para = doc.add_paragraph()
        para.style = self._get_safe_style(doc, style_name)
        para.add_run(text)
        return para
    
    def _handle_error(self, operation: str, doc_name: str = None, error: Exception = None) -> Dict[str, Any]:
        """Handle errors and return a structured error response."""
        error_msg = f"Error {operation}: {str(error)}" if error else f"Error {operation}"
        print(error_msg)
        return {"document_name": doc_name, "analysis": error_msg} if doc_name else error_msg
    
    def _parse_markdown_line(self, doc: docx.Document, line: str) -> docx.text.paragraph.Paragraph:
        """Parse a Markdown line and apply appropriate Word styles."""
        # Check for Markdown headings (e.g., ## Heading)
        heading_match = re.match(r'^(#+)\s+(.+)$', line.strip())
        if heading_match:
            level = len(heading_match.group(1))  # Number of # symbols
            heading_text = heading_match.group(2).strip()
            # Map Markdown heading levels to Word styles
            style_map = {1: 'Heading 1', 2: 'Heading 2', 3: 'Heading 3'}
            style_name = style_map.get(level, 'Normal')
            para = doc.add_paragraph()
            para.style = self._get_safe_style(doc, style_name)
            para.add_run(heading_text)
            return para
        
        # Process non-heading lines with bold text
        para = doc.add_paragraph()
        para.style = self._get_safe_style(doc, 'Normal')
        if line.strip():
            parts = line.split('**')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Bold text between **
                    para.add_run(part).bold = True
                else:
                    para.add_run(part)
        return para
    
    def process_document_set(self, doc_set: Dict[str, List[str]], input_dir: Path) -> Dict[str, Any]:
        """Process a set of documents and generate a summary."""
        set_name = doc_set['name']
        documents = doc_set['documents']
        document_analyses = []
        
        for doc_name in documents:
            doc_path = input_dir / doc_name
            try:
                print(f"\nProcessing document: {doc_name}")
                doc = docx.Document(doc_path)
                text_content = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                doc_analysis = self.analyze_document(text_content, doc_name)
                document_analyses.append(doc_analysis)
            except Exception as e:
                document_analyses.append(self._handle_error("processing document", doc_name, e))
        
        set_summary = self.generate_comprehensive_summary(document_analyses)
        return {
            "set_name": set_name,
            "summary": set_summary,
            "documents": documents
        }
    
    def analyze_document(self, text: str, doc_name: str) -> Dict[str, Any]:
        """Analyze a single document using the LLM client."""
        try:
            analysis = self.llm_client.generate_summary(
                text,
                max_length=1000,
                sections=["main topic and purpose", "key points and findings", "important context", "critical information", "recommendations"]
            )
            return {"document_name": doc_name, "analysis": analysis}
        except Exception as e:
            return self._handle_error("analyzing document", doc_name, e)
    
    def generate_comprehensive_summary(self, document_analyses: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive summary of multiple document analyses."""
        try:
            prompt = f"""
            Create a comprehensive summary of the following documents.
            Document Analyses: {json.dumps(document_analyses, indent=2)}
            Include: Executive Summary, Key Findings, Important Context, Critical Information, Cross-Document Insights, Recommendations
            Format with clear sections and use **bold** for important terms.
            """
            return self.llm_client.generate_content(prompt)
        except Exception as e:
            return self._handle_error("generating comprehensive summary", error=e)
    
    def create_context_document(self, document_sets: List[Dict[str, List[str]]], input_dir: Path, output_file: str) -> docx.Document:
        """Create a Word document with summaries for each document set."""
        doc = docx.Document()
        self._init_document_styles(doc)
        
        self._add_styled_paragraph(doc, f"Document Set Analysis: {output_file}", 'Heading 1')
        self._add_styled_paragraph(doc, "Table of Contents", 'Heading 2')
        
        for i, doc_set in enumerate(document_sets, 1):
            self._add_styled_paragraph(doc, f"{i}. {doc_set['name']}", 'Normal')
            self._add_styled_paragraph(doc, f"{i}. {doc_set['name']}", 'Heading 2')
            
            set_info = self.process_document_set(doc_set, input_dir)
            
            self._add_styled_paragraph(doc, "Summary", 'Heading 3')
            
            summary_text = set_info['summary']
            paragraphs = summary_text.split('\n')
            for para_text in paragraphs:
                if para_text.strip():
                    self._parse_markdown_line(doc, para_text)
            
            doc.add_paragraph("---" * 20, style=self._get_safe_style(doc, 'Normal'))
        
        return doc