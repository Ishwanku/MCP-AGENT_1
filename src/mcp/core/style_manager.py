from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.styles.style import _ParagraphStyle
import logging

logger = logging.getLogger(__name__)

class StyleManager:
    # The style_configs dictionary defines custom styles for the document
    def __init__(self):
        self.style_configs = {
            "CustomTitle": {
                "font_name": "Calibri Light",
                "size": 24,
                "bold": True,
                "alignment": WD_ALIGN_PARAGRAPH.CENTER,
                "space_after": 12,
            },
            "SectionHeader": {
                "font_name": "Calibri",
                "size": 16,
                "bold": True,
                "space_before": 12,
                "space_after": 6,
            },
            "Heading 3": {
                "font_name": "Calibri",
                "size": 14,
                "bold": True,
                "space_before": 12,
                "space_after": 4,
            },
            "Heading 4": {
                "font_name": "Calibri",
                "size": 12,
                "bold": True,
                "space_before": 10,
                "space_after": 4,
            },
            "Heading 5": {
                "font_name": "Calibri",
                "size": 11,
                "bold": True,
                "space_before": 8,
                "space_after": 4,
            },
            "Heading 6": {
                "font_name": "Calibri",
                "size": 11,
                "bold": True,
                "space_before": 6,
                "space_after": 4,
            },
            "Summary": {
                "font_name": "Calibri",
                "size": 11,
                "bold": False,
                "line_spacing": 1.15,
                "space_after": 6,
            },
            "ImportantInfo": {
                "font_name": "Calibri",
                "size": 11,
                "bold": True,
                "left_indent": 36,
                "space_after": 6,
            },
            "List Bullet": {
                "font_name": "Calibri",
                "size": 11,
                "bold": False,
                "left_indent": 36,
                "space_after": 6,
            },
        }

    # A helper method to set the font name, size, and boldness for a given style.
    def set_style_properties(
        self,
        style,
        font_name: str = "Calibri",
        size: int = 11,
        bold: bool = False,
    ):
        """Set common style properties for a given style."""
        style.font.name = font_name
        style.font.size = Pt(size)
        style.font.bold = bold

    # This method initializes all the custom styles in a given Document object.
    def init_document_styles(self, doc: Document) -> None:
        """Initialize document styles with proper formatting."""
        try:
            for style_name, config in self.style_configs.items():
                if style_name not in doc.styles:
                    style = doc.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                else:
                    style = doc.styles[style_name]
                self.set_style_properties(
                    style,
                    font_name=config["font_name"],
                    size=config["size"],
                    bold=config.get("bold", False),
                )
                if "alignment" in config:
                    style.paragraph_format.alignment = config["alignment"]
                if "space_before" in config:
                    style.paragraph_format.space_before = Pt(config["space_before"])
                if "space_after" in config:
                    style.paragraph_format.space_after = Pt(config["space_after"])
                if "line_spacing" in config:
                    style.paragraph_format.line_spacing = config["line_spacing"]
                if "left_indent" in config:
                    style.paragraph_format.left_indent = Pt(config["left_indent"])
        except Exception as e:
            logger.error(f"Error initializing document styles: {str(e)}")
            raise

    # If the requested style does not exist, it falls back to the default "Normal" style.
    def get_safe_style(
        self, doc: Document, style_name: str
    ) -> _ParagraphStyle:
        """Get a style from the document, falling back to 'Normal' if not found."""
        try:
            return doc.styles[style_name]
        except KeyError:
            return doc.styles["Normal"]