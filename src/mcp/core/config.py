from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

# Instantiate settings for use throughout the application
settings = Settings()