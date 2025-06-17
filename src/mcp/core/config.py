from pydantic_settings import BaseSettings
from typing import Optional, List, Tuple
from pydantic import field_validator, Field

class DocumentStyleSettings(BaseSettings):
    font_name: str = "Arial"
    size: int = 11
    bold: bool = False
    color: Optional[Tuple[int, int, int]] = None
    alignment: Optional[str] = None
    space_before: Optional[int] = None
    space_after: Optional[int] = None
    left_indent: Optional[int] = None

class Settings(BaseSettings):
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    DOCUMENT_AGENT_PORT: int = 8000
    DOCUMENT_AGENT_API_KEY: str = "your_api_key_here"
    OUTPUT_DIR: str = "output"
    API_BASE_URL: str = "http://127.0.0.1:8000"

    # Azure AI Foundry settings
    LLM_PROVIDER: str = "azure"
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    
    # Azure AI Search settings
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_KEY: str = ""
    AZURE_SEARCH_INDEX_NAME: str = "documents"


    # Document Style Settings
    title_style: DocumentStyleSettings = Field(
        default_factory=lambda: DocumentStyleSettings(
            font_name="Arial",
            size=24,
            bold=True,
            color=(192, 80, 77),
            alignment="center",
            space_after=12
        )
    )
    
    heading1_style: DocumentStyleSettings = Field(
        default_factory=lambda: DocumentStyleSettings(
            font_name="Arial",
            size=18,
            bold=True,
            color=(68, 114, 196),
            space_before=12,
            space_after=6
        )
    )
    
    heading2_style: DocumentStyleSettings = Field(
        default_factory=lambda: DocumentStyleSettings(
            font_name="Arial",
            size=16,
            bold=True,
            space_before=12,
            space_after=6
        )
    )
    
    heading3_style: DocumentStyleSettings = Field(
        default_factory=lambda: DocumentStyleSettings(
            font_name="Arial",
            size=14,
            bold=True,
            space_before=12,
            space_after=6
        )
    )
    
    normal_style: DocumentStyleSettings = Field(
        default_factory=lambda: DocumentStyleSettings(
            font_name="Arial",
            size=11,
            space_after=6
        )
    )
    
    list_bullet_style: DocumentStyleSettings = Field(
        default_factory=lambda: DocumentStyleSettings(
            font_name="Arial",
            size=11,
            left_indent=36,
            space_after=6
        )
    )

    # LLM Settings
    LLM_DEFAULT_MAX_TOKENS: int = 1000
    LLM_DEFAULT_TEMPERATURE: float = 0.7

    # Document Set Default Settings
    DEFAULT_SUMMARY_TYPE: str = "detailed"
    DEFAULT_INCLUDE_SECTIONS: List[str] = [
        "executive_summary",
        "important_information"
    ]

    @field_validator('AZURE_OPENAI_ENDPOINT')
    def validate_endpoint(cls, v):
        if not v.startswith('https://'):
            raise ValueError('AZURE_OPENAI_ENDPOINT must be a valid HTTPS URL')
        return v

    @field_validator('AZURE_OPENAI_API_KEY')
    def validate_api_key(cls, v):
        if not v:
            raise ValueError('AZURE_OPENAI_API_KEY is required')
        return v

    @field_validator('AZURE_OPENAI_DEPLOYMENT_NAME')
    def validate_deployment_name(cls, v):
        if not v:
            raise ValueError('AZURE_OPENAI_DEPLOYMENT_NAME is required')
        return v

    @field_validator('AZURE_SEARCH_ENDPOINT')
    def validate_search_endpoint(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('AZURE_SEARCH_ENDPOINT must be a valid HTTPS URL')
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields in environment variables

# Instantiate settings for use throughout the application
settings = Settings()