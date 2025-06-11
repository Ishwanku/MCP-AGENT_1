from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server settings
    DOCUMENT_AGENT_PORT: int = 8000
    DOCUMENT_AGENT_API_KEY: str = "your_api_key_here"
    OUTPUT_DIR: str = "output"

    # LLM settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = "AIzaSyBhQ0o8r9LkYtRkV8i24825ZUa3UIheUns"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instantiate settings for use throughout the application
settings = Settings()