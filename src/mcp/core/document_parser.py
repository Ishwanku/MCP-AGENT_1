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
import markdown2
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


# Document parser class to process, analyze and summarize
class DocumentParser:

    # If user give the llm_client then it uses that if not given then it makes default LLMClient by using setting()
    def __init__(self):
        self.settings = Settings()
        self.llm_client = LLMClient(settings=self.settings)
        self.chunk_size = 4000  # Slightly less than 5000 to account for prompt overhead
        self.chunk_overlap = 200  # Overlap between chunks to maintain context

    # Method to set common style properties
    def _set_style_properties(
        self,
        style,
        font_name: str = "Calibri",
        size: int = 11,
        bold: bool = False,
        color: RGBColor = None,
    ):
        """Set common style properties for a given style."""
        style.font.name = font_name
        style.font.size = Pt(size)
        style.font.bold = bold
        if color:
            style.font.color.rgb = color

    # Method to initialize document styles
    def _init_document_styles(self, doc: Document) -> None:
        """Initialize document styles with proper formatting."""
        try:
            # Title style
            title_style = doc.styles.add_style("CustomTitle", WD_STYLE_TYPE.PARAGRAPH)
            self._set_style_properties(title_style, "Calibri Light", 24, True)
            title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_style.paragraph_format.space_after = Pt(12)

            # Section Header style
            section_style = doc.styles.add_style(
                "SectionHeader", WD_STYLE_TYPE.PARAGRAPH
            )
            self._set_style_properties(section_style, "Calibri", 16, True)
            section_style.paragraph_format.space_before = Pt(12)
            section_style.paragraph_format.space_after = Pt(6)

            # Only add custom heading styles if they do not already exist
            for heading_level, size in [(3, 14), (4, 12), (5, 11), (6, 11)]:
                style_name = f"Heading {heading_level}"
                if style_name not in doc.styles:
                    heading_style = doc.styles.add_style(
                        style_name, WD_STYLE_TYPE.PARAGRAPH
                    )
                    self._set_style_properties(heading_style, "Calibri", size, True)
                    heading_style.paragraph_format.space_before = Pt(
                        12 - (heading_level - 3) * 2
                    )
                    heading_style.paragraph_format.space_after = Pt(4)
                else:
                    # Modify existing style instead of adding
                    heading_style = doc.styles[style_name]
                    self._set_style_properties(heading_style, "Calibri", size, True)
                    heading_style.paragraph_format.space_before = Pt(
                        12 - (heading_level - 3) * 2
                    )
                    heading_style.paragraph_format.space_after = Pt(4)

            # Summary style
            summary_style = doc.styles.add_style("Summary", WD_STYLE_TYPE.PARAGRAPH)
            self._set_style_properties(summary_style, "Calibri", 11)
            summary_style.paragraph_format.line_spacing = 1.15
            summary_style.paragraph_format.space_after = Pt(6)

            # Important Information style
            important_style = doc.styles.add_style(
                "ImportantInfo", WD_STYLE_TYPE.PARAGRAPH
            )
            self._set_style_properties(important_style, "Calibri", 11, True)
            important_style.paragraph_format.left_indent = Pt(36)
            important_style.paragraph_format.space_after = Pt(6)

        except Exception as e:
            logger.error(f"Error initializing document styles: {str(e)}")
            raise

    # Method to get a safe style
    def _get_safe_style(
        self, doc: Document, style_name: str
    ) -> docx.styles.style._ParagraphStyle:
        """Get a style from the document, falling back to 'Normal' if not found."""
        try:
            return doc.styles[style_name]
        except KeyError:
            return doc.styles["Normal"]

    # Method to add a styled paragraph
    def _add_styled_paragraph(
        self, doc: Document, text: str, style_name: str
    ) -> docx.text.paragraph.Paragraph:
        """Add a styled paragraph to the document."""
        para = doc.add_paragraph()
        para.style = self._get_safe_style(doc, style_name)
        para.add_run(text)
        return para

    # Method to handle errors
    def _handle_error(
        self, operation: str, doc_name: str, error: Exception
    ) -> Dict[str, Any]:
        """Handle errors during document processing."""
        return {
            "document_name": doc_name,
            "error": f"Error {operation} {doc_name}: {str(error)}",
        }

    class DocxHTMLParser(HTMLParser):
        def __init__(self, doc, style_map):
            super().__init__()
            self.doc = doc
            self.style_map = style_map
            self.current_para = None
            self.current_style = "Normal"
            self.bold = False
            self.italic = False
            self.list_type = None
            self.list_level = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.current_style = self.style_map.get(tag, "Normal")
                self.current_para = self.doc.add_paragraph()
                self.current_para.style = self.current_style
                self.current_para.paragraph_format.space_after = Pt(1)
            elif tag == "p":
                self.current_style = "Normal"
                self.current_para = self.doc.add_paragraph()
                self.current_para.paragraph_format.space_after = Pt(1)
            elif tag in ("ul", "ol"):
                # Always use bullet points, even for ordered lists
                self.list_type = "List Bullet"
                self.list_level += 1
            elif tag == "li":
                self.current_para = self.doc.add_paragraph(style="List Bullet")
                self.current_para.paragraph_format.space_after = Pt(1)
            elif tag == "strong" or tag == "b":
                self.bold = True
            elif tag == "em" or tag == "i":
                self.italic = True

        def handle_endtag(self, tag):
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li"):
                self.current_para = None
            elif tag in ("ul", "ol"):
                self.list_type = None
                self.list_level = max(0, self.list_level - 1)
            elif tag == "strong" or tag == "b":
                self.bold = False
            elif tag == "em" or tag == "i":
                self.italic = False

        def handle_data(self, data):
            if not data.strip():
                return  # Skip empty data to avoid empty paragraphs
            if self.current_para is None:
                self.current_para = self.doc.add_paragraph()
                self.current_para.paragraph_format.space_after = Pt(1)
            run = self.current_para.add_run(data)
            run.bold = self.bold
            run.italic = self.italic

    # Method to process a document set and take out the text from the document then pass it to the LLM client to make the final summary
    async def process_document_set(
        self, doc_set: Dict[str, Any], input_dir: Path
    ) -> Dict[str, Any]:
        """Process a document set and generate a summary."""
        try:
            set_name = doc_set["name"]
            documents = doc_set["documents"]
            document_analyses = []

            for doc_name in documents:
                doc_path = input_dir / doc_name
                try:
                    doc = Document(doc_path)
                    text_content = "\n".join(
                        [para.text for para in doc.paragraphs if para.text.strip()]
                    )
                    doc_analysis = await self.analyze_document(text_content, doc_name)
                    document_analyses.append(doc_analysis)
                except Exception as e:
                    document_analyses.append(
                        self._handle_error("processing document", doc_name, e)
                    )

            set_summary = await self.generate_comprehensive_summary(document_analyses)
            return {
                "set_name": set_name,
                "summary": set_summary,
                "documents": documents,
            }
        except Exception as e:
            logger.error(f"Error processing document set: {str(e)}")
            return {
                "set_name": doc_set.get("name", "Unknown"),
                "summary": f"Error processing document set: {str(e)}",
                "documents": doc_set.get("documents", []),
            }

    def chunk_document(self, text: str) -> List[str]:
        """Split document into overlapping chunks."""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position for this chunk
            end = start + self.chunk_size

            # If this is not the first chunk, include some overlap from previous chunk
            if start > 0:
                start = start - self.chunk_overlap

            # If this is the last chunk, take all remaining text
            if end >= text_length:
                chunks.append(text[start:])
                break

            # Find the last period or newline in the chunk to break at a natural point
            last_period = text.rfind(".", start, end)
            last_newline = text.rfind("\n", start, end)
            break_point = max(last_period, last_newline)

            if break_point > start:
                end = break_point + 1

            chunks.append(text[start:end])
            start = end

        return chunks

    async def analyze_document(self, text: str, doc_name: str) -> Dict[str, Any]:
        """Analyze a document and extract key information."""
        try:
            # Split document into chunks
            chunks = self.chunk_document(text)
            chunk_analyses = []

            # Process each chunk
            for i, chunk in enumerate(chunks, 1):
                prompt = f"""
                Analyze this part of the document (Part {i} of {len(chunks)}) and provide:
                1. A concise summary of the main content
                2. Any critical or important information that needs special attention

                Document: {doc_name}
                Content: {chunk}
                """

                chunk_analysis = await self.llm_client.generate_content(prompt)
                if chunk_analysis:
                    chunk_analyses.append(chunk_analysis)

            # Combine chunk analyses
            if not chunk_analyses:
                return {
                    "document_name": doc_name,
                    "analysis": "No analysis available - document may be empty or unreadable",
                }

            # Create final summary of all chunks
            summary_prompt = f"""
            Create a comprehensive analysis of this document by combining the analyses of its parts.
            Focus on two main aspects:
            1. Executive Summary: Provide a clear, concise summary of the entire document
            2. Important Information: List any critical points, key findings, or information that requires special attention

            Document: {doc_name}
            Part Analyses:
            {chr(10).join([f"Part {i+1}: {analysis}" for i, analysis in enumerate(chunk_analyses)])}
            """

            final_analysis = await self.llm_client.generate_content(summary_prompt)

            return {
                "document_name": doc_name,
                "analysis": final_analysis or "No analysis available",
            }

        except Exception as e:
            logger.error(f"Error analyzing document {doc_name}: {str(e)}")
            return {
                "document_name": doc_name,
                "analysis": f"Error analyzing document: {str(e)}",
            }

    async def generate_comprehensive_summary(
        self, document_analyses: List[Dict[str, Any]]
    ) -> str:
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

    # Method to format text by converting markdown to Word formatting using markdown2 and HTMLParser
    def _format_text(self, text: str, paragraph) -> None:
        """Format text by converting markdown to Word formatting using markdown2 and HTMLParser."""
        try:
            doc = paragraph._parent
            # Convert markdown to HTML
            html = markdown2.markdown(text)
            # Map HTML tags to Word styles
            style_map = {
                "h1": "CustomTitle",
                "h2": "SectionHeader",
                "h3": "Heading 3",
                "h4": "Heading 4",
                "h5": "Heading 5",
                "h6": "Heading 6",
            }
            parser = self.DocxHTMLParser(doc, style_map)
            parser.feed(html)
        except Exception as e:
            logger.error(f"Error formatting text: {str(e)}")
            paragraph.add_run(text)

    # Crea
    def create_context_document(
        self, document_sets: List[Dict[str, Any]], input_dir: Path, output_file: str
    ) -> Document:
        """Create a context document from processed document sets."""
        try:
            doc = Document()
            self._init_document_styles(doc)
            title = doc.add_paragraph("Merged Document")
            title.style = doc.styles["CustomTitle"]
            # Process each document set
            for set_info in document_sets:
                try:
                    # Add section header
                    header = doc.add_paragraph(set_info["set_name"])
                    header.style = doc.styles["SectionHeader"]
                    # Add summary section (without 'Executive Summary' heading)
                    if set_info.get("summary"):
                        summary_para = doc.add_paragraph()
                        self._format_text(set_info["summary"], summary_para)
                        summary_para.style = doc.styles["Summary"]
                    # Add important information section
                    if set_info.get("important_info"):
                        important_header = doc.add_paragraph("Important Information")
                        important_header.style = doc.styles["SectionHeader"]
                        important_para = doc.add_paragraph()
                        self._format_text(set_info["important_info"], important_para)
                        important_para.style = doc.styles["ImportantInfo"]
                    # Add document list
                    docs_header = doc.add_paragraph("Documents Analyzed")
                    docs_header.style = doc.styles["SectionHeader"]
                    for doc_path in set_info.get("documents", []):
                        doc_name = Path(doc_path).name
                        bullet_para = doc.add_paragraph(style="List Bullet")
                        bullet_para.add_run(doc_name)
                    # Add spacing between sections
                    doc.add_paragraph()
                except Exception as e:
                    logger.error(
                        f"Error processing set {set_info.get('set_name', 'Unknown')}: {str(e)}"
                    )
                    continue
            return doc
        except Exception as e:
            logger.error(f"Error creating context document: {str(e)}")
            raise
