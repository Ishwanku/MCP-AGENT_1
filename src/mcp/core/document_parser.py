import json
import re
from pathlib import Path
from typing import Dict, List, Any
import docx
from docx import Document
from docx.shared import Pt, RGBColor
from .llm_client import LLMClient
from .config import Settings
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import logging
import time

logger = logging.getLogger(__name__)

# Document parser class to process, analyze and summarize
class DocumentParser:

    # If user give the llm_client then it uses that if not given then it makes default LLMClient by using setting() 
    def __init__(self):
        self.settings = Settings()
        self.llm_client = LLMClient(settings=self.settings)
    
    # Method to set common style properties
    def _set_style_properties(self, style, font_name: str = 'Arial', size: int = 11, bold: bool = False):
        """Set common style properties for a given style."""
        style.font.name = font_name
        style.font.size = Pt(size)
        style.font.bold = bold
    
    # Method to initialize document styles
    def _init_document_styles(self, doc: Document) -> None:
        """Initialize document styles."""
        try:
            # Title style
            title_style = doc.styles['Title']
            self._set_style_properties(
                title_style,
                font_name=self.settings.title_style.font_name,
                size=self.settings.title_style.size,
                bold=self.settings.title_style.bold
            )
            if self.settings.title_style.color:
                title_style.font.color.rgb = RGBColor(*self.settings.title_style.color)
            if self.settings.title_style.alignment == "center":
                title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if self.settings.title_style.space_after:
                title_style.paragraph_format.space_after = Pt(self.settings.title_style.space_after)
            
            # Heading 1 style
            h1_style = doc.styles['Heading 1']
            self._set_style_properties(
                h1_style,
                font_name=self.settings.heading1_style.font_name,
                size=self.settings.heading1_style.size,
                bold=self.settings.heading1_style.bold
            )
            if self.settings.heading1_style.color:
                h1_style.font.color.rgb = RGBColor(*self.settings.heading1_style.color)
            if self.settings.heading1_style.space_before:
                h1_style.paragraph_format.space_before = Pt(self.settings.heading1_style.space_before)
            if self.settings.heading1_style.space_after:
                h1_style.paragraph_format.space_after = Pt(self.settings.heading1_style.space_after)
            
            # Heading 2 style
            h2_style = doc.styles['Heading 2']
            self._set_style_properties(
                h2_style,
                font_name=self.settings.heading2_style.font_name,
                size=self.settings.heading2_style.size,
                bold=self.settings.heading2_style.bold
            )
            if self.settings.heading2_style.space_before:
                h2_style.paragraph_format.space_before = Pt(self.settings.heading2_style.space_before)
            if self.settings.heading2_style.space_after:
                h2_style.paragraph_format.space_after = Pt(self.settings.heading2_style.space_after)
            
            # Heading 3 style
            h3_style = doc.styles['Heading 3']
            self._set_style_properties(
                h3_style,
                font_name=self.settings.heading3_style.font_name,
                size=self.settings.heading3_style.size,
                bold=self.settings.heading3_style.bold
            )
            if self.settings.heading3_style.space_before:
                h3_style.paragraph_format.space_before = Pt(self.settings.heading3_style.space_before)
            if self.settings.heading3_style.space_after:
                h3_style.paragraph_format.space_after = Pt(self.settings.heading3_style.space_after)
            
            # Normal style
            normal_style = doc.styles['Normal']
            self._set_style_properties(
                normal_style,
                font_name=self.settings.normal_style.font_name,
                size=self.settings.normal_style.size
            )
            if self.settings.normal_style.space_after:
                normal_style.paragraph_format.space_after = Pt(self.settings.normal_style.space_after)
            
            # List Bullet style
            list_bullet_style = doc.styles['List Bullet']
            self._set_style_properties(
                list_bullet_style,
                font_name=self.settings.list_bullet_style.font_name,
                size=self.settings.list_bullet_style.size
            )
            if self.settings.list_bullet_style.left_indent:
                list_bullet_style.paragraph_format.left_indent = Pt(self.settings.list_bullet_style.left_indent)
            if self.settings.list_bullet_style.space_after:
                list_bullet_style.paragraph_format.space_after = Pt(self.settings.list_bullet_style.space_after)
            
        except Exception as e:
            logger.error(f"Error initializing document styles: {str(e)}")
            raise Exception(f"Failed to initialize document styles: {str(e)}")
    
    # Method to get a safe style
    def _get_safe_style(self, doc: Document, style_name: str) -> docx.styles.style._ParagraphStyle:
        """Get a style from the document, falling back to 'Normal' if not found."""
        try:
            return doc.styles[style_name]
        except KeyError:
            return doc.styles['Normal']
    
    # Method to add a styled paragraph
    def _add_styled_paragraph(self, doc: Document, text: str, style_name: str) -> docx.text.paragraph.Paragraph:
        """Add a styled paragraph to the document."""
        para = doc.add_paragraph()
        para.style = self._get_safe_style(doc, style_name)
        para.add_run(text)
        return para
    
    # Method to handle errors
    def _handle_error(self, operation: str, doc_name: str, error: Exception) -> Dict[str, Any]:
        """Handle errors during document processing."""
        return {
            "document_name": doc_name,
            "error": f"Error {operation} {doc_name}: {str(error)}"
        }
    
    # Method to parse a Markdown line (#, ##, ###, etc.)
    def _parse_markdown_line(self, doc: Document, line: str) -> docx.text.paragraph.Paragraph:
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
    
    # Method to process a document set and take out the text from the document then pass it to the LLM client to make the final summary 
    async def process_document_set(self, doc_set: Dict[str, Any], input_dir: Path) -> Dict[str, Any]:
        """Process a document set and generate a summary."""
        try:
            set_name = doc_set['name']
            documents = doc_set['documents']
            document_analyses = []
            
            for doc_name in documents:
                doc_path = input_dir / doc_name
                try:
                    doc = Document(doc_path)
                    text_content = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                    doc_analysis = await self.analyze_document(text_content, doc_name)
                    document_analyses.append(doc_analysis)
                except Exception as e:
                    document_analyses.append(self._handle_error("processing document", doc_name, e))
            
            set_summary = await self.generate_comprehensive_summary(document_analyses)
            return {
                "set_name": set_name,
                "summary": set_summary,
                "documents": documents
            }
        except Exception as e:
            logger.error(f"Error processing document set: {str(e)}")
            return {
                "set_name": doc_set.get('name', 'Unknown'),
                "summary": f"Error processing document set: {str(e)}",
                "documents": doc_set.get('documents', [])
            }
    
    async def analyze_document(self, text: str, doc_name: str) -> Dict[str, Any]:
        """Analyze a document and extract key information."""
        try:
            # Create a focused prompt for the LLM
            prompt = f"""
            Analyze this document and provide a concise summary focusing on:
            1. Main Points
            2. Document Summary
            3. Key Findings
            4. Important Information

            Document: {doc_name}
            Content: {text[:5000]}  # Limit content length to avoid token limits
            """
            
            analysis = await self.llm_client.generate_content(prompt)
            
            if not analysis:
                return {
                    "document_name": doc_name,
                    "analysis": "No analysis available - document may be empty or unreadable"
                }
                
            return {
                "document_name": doc_name,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"Error analyzing document {doc_name}: {str(e)}")
            return {
                "document_name": doc_name,
                "analysis": f"Error analyzing document: {str(e)}"
            }
    
    async def generate_comprehensive_summary(self, document_analyses: List[Dict[str, Any]]) -> str:
        """Generate a focused summary for a pair of documents."""
        try:
            if not document_analyses:
                return "No documents available for analysis"
                
            # Create a focused prompt for the LLM
            prompt = f"""
            Create a concise summary of these related documents, focusing on:
            1. Main Points
            2. Document Summaries
            3. Key Findings
            4. Important Information

            Documents:
            {chr(10).join([f"- {analysis['document_name']}: {analysis.get('analysis', 'No analysis available')}" for analysis in document_analyses])}
            """
            
            summary = await self.llm_client.generate_content(prompt)
            
            if not summary:
                return "Unable to generate summary - please check document contents"
                
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"
    
    # Method to format text by converting markdown to Word formatting
    def _format_text(self, text: str, paragraph) -> None:
        """Format text by converting markdown to Word formatting."""
        try:
            # Split text by markdown patterns
            parts = re.split(r'(#{1,6}\s+|\*\*.*?\*\*|\*.*?\*)', text)
            
            for part in parts:
                if not part.strip():
                    continue
                    
                # Handle headings
                if part.startswith('#'):
                    level = len(re.match(r'^#+', part).group())
                    text = part.lstrip('#').strip()
                    run = paragraph.add_run(text)
                    run.bold = True
                    run.font.size = Pt(18 - (level * 2))  # Decrease size for each level
                    continue
                    
                # Handle bold text
                if part.startswith('**') and part.endswith('**'):
                    text = part[2:-2]
                    run = paragraph.add_run(text)
                    run.bold = True
                    continue
                    
                # Handle italic text
                if part.startswith('*') and part.endswith('*'):
                    text = part[1:-1]
                    run = paragraph.add_run(text)
                    run.italic = True
                    continue
                    
                # Regular text
                paragraph.add_run(part)
        except Exception as e:
            logger.error(f"Error formatting text: {str(e)}")
            # Add error text as plain text
            paragraph.add_run(text)
    
    # Crea
    def create_context_document(self, document_sets: List[Dict[str, Any]], input_dir: Path, output_file: str) -> Document:
        """Create a context document from processed document sets."""
        try:
            doc = Document()
            self._init_document_styles(doc)
            
            # Add title
            title = doc.add_paragraph("Document Context Summary")
            title.style = doc.styles['Title']
            
            # Process each document set
            for set_info in document_sets:
                try:
                    # Add section header (use the set_name directly as it already includes section number)
                    header = doc.add_paragraph(set_info['set_name'])
                    header.style = doc.styles['Heading 1']
                    
                    # Add summary
                    if set_info.get('summary'):
                        summary_para = doc.add_paragraph("Summary:")
                        summary_para.style = doc.styles['Heading 2']
                        self._format_text(set_info['summary'], doc.add_paragraph())
                    
                    # Add document list with just names
                    docs_para = doc.add_paragraph("Documents for reference:")
                    docs_para.style = doc.styles['Heading 2']
                    for doc_path in set_info.get('documents', []):
                        # Extract just the filename from the path
                        doc_name = Path(doc_path).name
                        bullet_para = doc.add_paragraph(style='List Bullet')
                        bullet_para.add_run(doc_name)
                    
                    # Add spacing
                    doc.add_paragraph()
                except Exception as e:
                    logger.error(f"Error processing set {set_info.get('set_name', 'Unknown')}: {str(e)}")
                    continue
            
            return doc
        except Exception as e:
            logger.error(f"Error creating context document: {str(e)}")
            raise