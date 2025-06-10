"""
Configuration Settings for MCP Document Merge Agent

This module manages configuration settings for the MCP Document Merge Agent using Pydantic's BaseSettings.
It loads settings from environment variables and `.env` files, ensuring type safety and providing
default values for the application.

Key Features:
- Loads configuration from environment variables or `.env` files.
- Provides type validation for settings to prevent configuration errors.
- Supports settings for server operation, output directories, logging, and LLM providers.

Usage:
    The settings defined here are used throughout the application to configure server behavior,
    API authentication, output storage, logging levels, and LLM provider selection for summarization.
    Access the settings via the `settings` instance created at the module's end.

Configuration:
    Key settings include:
    - DOCUMENT_AGENT_PORT: Port for the FastAPI server (default: 8000).
    - DOCUMENT_AGENT_API_KEY: Optional API key for securing endpoints.
    - OUTPUT_DIR: Directory for storing merged documents.
    - LOG_LEVEL: Logging verbosity (default: INFO).
    - LLM_PROVIDER: Selects the LLM for summarization (e.g., ollama, openai, gemini).
    - Specific API keys and models for each LLM provider (e.g., OPENAI_API_KEY, GEMINI_MODEL).
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Settings for the MCP Document Merge Agent.
    
    This class defines the configuration attributes for the application, loaded from environment
    variables or a `.env` file. It uses Pydantic for validation and type safety.
    
    Attributes:
        DOCUMENT_AGENT_PORT (int): Port to run the document agent on.
        DOCUMENT_AGENT_API_KEY (Optional[str]): API key for authentication.
        OUTPUT_DIR (Optional[str]): Directory for output Word documents.
        LOG_LEVEL (str): Logging level for the application.
        LLM_PROVIDER (str): The LLM provider to use for summarization (e.g., 'ollama' or 'openai').
        LLM_MODEL (str): The local LLM model to use for summarization (e.g., qwen2:7b-instruct).
        OPENAI_API_KEY (Optional[str]): API key for OpenAI.
        OPENAI_MODEL (str): Model for OpenAI.
        GEMINI_API_KEY (Optional[str]): API key for Gemini.
        GEMINI_MODEL (str): Model for Gemini.
    """
    
    # Document Agent settings for server configuration
    DOCUMENT_AGENT_PORT: int = 8000
    DOCUMENT_AGENT_API_KEY: Optional[str] = None
    
    # Output settings for merged document storage
    OUTPUT_DIR: Optional[str] = None
    
    # Logging settings for application monitoring
    LOG_LEVEL: str = "INFO"
    
    # LLM settings for summarization and context extraction
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen2:7b-instruct"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro-latest"
    
    class Config:
        """
        Pydantic configuration for Settings.
        
        This inner class specifies configuration options for loading environment variables.
        
        Attributes:
            env_file (str): Name of the environment file to load.
            case_sensitive (bool): Whether environment variable names are case-sensitive.
        """
        env_file = ".env"
        case_sensitive = True

# Instantiate settings for use throughout the application
settings = Settings()