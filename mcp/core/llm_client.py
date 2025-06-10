"""
LLM Client for MCP Document Merge Agent

This module provides a unified interface for interacting with various Large Language Model (LLM)
providers for text summarization or context extraction in the MCP Document Merge Agent.
It supports multiple providers like Ollama, OpenAI, and Gemini, dynamically selecting the provider
based on configuration settings.

Key Features:
- Abstracts LLM provider interactions behind a single client interface.
- Supports Ollama for local LLM deployments, OpenAI for cloud-based GPT models, and Gemini for Google's AI services.
- Handles provider initialization, API key management, and availability checks.
- Includes fallback to direct HTTP requests for Gemini API to bypass library authentication issues.
- Provides detailed logging for initialization and content generation errors.

Usage:
    The LLMClient is instantiated once and used throughout the application for summarization tasks.
    It is initialized with the provider and model specified in the configuration (via environment variables
    or `.env` file). The `generate_content` method is used to request summaries or context from documents.

Configuration:
    Key settings from `config.py` include:
    - LLM_PROVIDER: Specifies the provider (ollama, openai, gemini).
    - LLM_MODEL: Default model for Ollama.
    - OPENAI_API_KEY and OPENAI_MODEL for OpenAI provider.
    - GEMINI_API_KEY and GEMINI_MODEL for Gemini provider.

Error Handling:
    Handles initialization failures, API quota limits (especially for Gemini), and authentication issues,
    with fallbacks to ensure the application continues to function even if summarization is unavailable.
"""

from typing import Optional, Dict, Any
import os
import logging
import requests

# Set up logging for detailed debugging and monitoring
logger = logging.getLogger(__name__)

# Attempt to import Ollama client and set availability flag
try:
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Ollama client not available. Summarization with Ollama will be disabled.")

# Attempt to import OpenAI client and set availability flag
try:
    from openai import OpenAI as OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI client not available. Summarization with OpenAI will be disabled.")

# Attempt to import Gemini client and set availability flag
try:
    import google.ai.generativelanguage as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Gemini client not available. Summarization with Gemini will be disabled.")

# Import configuration settings for LLM provider selection and API keys
from .config import settings

class LLMClient:
    """
    A unified client for interacting with different LLM providers.
    
    This class initializes the appropriate client based on the configured LLM provider
    in environment variables and provides a consistent interface for text summarization.
    
    Attributes:
        provider (str): The configured LLM provider ('ollama', 'openai', or 'gemini').
        client (Any): The initialized client instance for the selected provider.
    
    Methods:
        summarize_text(text: str, max_length: int = 200) -> str:
            Summarizes the given text using the configured LLM provider.
        is_available() -> bool:
            Checks if the LLM provider is available and initialized.
        generate_content(prompt: str) -> str:
            Generates content based on a given prompt using the configured provider.
    """
    
    def __init__(self):
        """
        Initialize the LLM client based on environment configuration.
        
        Sets up the appropriate client (Ollama, OpenAI, or Gemini) based on the
        LLM_PROVIDER environment variable and corresponding API keys or settings.
        Logs initialization status and performs connectivity tests for Gemini.
        """
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        logger.info(f"Initializing LLM client with provider: {self.provider}, model: {self.model}")
        if self.provider == "ollama":
            self.client = OllamaClient(model=settings.LLM_MODEL)
        elif self.provider == "openai":
            self.client = OpenAIClient(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
        elif self.provider == "gemini":
            logger.info(f"Setting up Gemini client with model: {settings.GEMINI_MODEL}, API key provided: {'Yes' if settings.GEMINI_API_KEY else 'No'}")
            if settings.GEMINI_API_KEY and GEMINI_AVAILABLE:
                try:
                    # Use a direct API key approach similar to curl request to bypass library issues
                    self.client = None
                    self.model = settings.GEMINI_MODEL
                    self.api_key = settings.GEMINI_API_KEY
                    logger.info("Gemini client initialized with direct API key approach. Testing API connectivity...")
                    # Test a simple content generation to verify API key permissions
                    test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={self.api_key}"
                    test_payload = {
                        "contents": [{
                            "parts": [{"text": "Test prompt"}]
                        }]
                    }
                    test_headers = {"Content-Type": "application/json"}
                    test_response = requests.post(test_url, json=test_payload, headers=test_headers)
                    if test_response.status_code == 200:
                        logger.info("Gemini API connectivity test successful with direct API key.")
                        self.client = "direct_api"
                    else:
                        logger.error(f"Gemini API test failed with status code {test_response.status_code}: {test_response.text}")
                        self.client = None
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini client: {e}")
                    self.client = None
            else:
                logger.error("Gemini API key not provided or package not available.")
                self.client = None
        else:
            logger.warning(f"Unknown LLM provider: {self.provider}. Falling back to Ollama.")
            self.client = OllamaClient(model=settings.LLM_MODEL)
        
        if not hasattr(self, 'client') or self.client is None or (self.provider != "gemini" and not hasattr(self.client, 'is_available')) or (self.provider != "gemini" and not self.client.is_available()):
            logger.error(f"Selected LLM provider {self.provider} is not available.")
        else:
            logger.info(f"LLM provider {self.provider} initialized successfully.")
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Summarize the given text using the configured LLM provider.
        
        This method constructs a prompt for summarization, focusing on extracting key points
        and context from the input text. It handles different providers with specific API calls.
        
        Args:
            text (str): The text to summarize.
            max_length (int): The approximate maximum length of the summary in words.
        
        Returns:
            str: The summarized text or an error message if summarization fails.
        """
        if len(text.strip()) < 50:
            return text  # Return original text if it's too short to process
        
        prompt = (
            f"Extract the most important context and key points from the following text in approximately {max_length} words. "
            "Focus on critical information, main themes, and essential details that provide a clear understanding of the document's purpose and content:\n\n"
            f"{text}"
        )
        
        try:
            if self.provider == "ollama":
                if not OLLAMA_AVAILABLE or self.client is None:
                    return "Context extraction unavailable: Ollama client not installed or not accessible."
                response = self.client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant skilled in extracting important context from documents."},
                        {"role": "user", "content": prompt}
                    ],
                    options={"temperature": 0.3}
                )
                return response['message']['content']
            elif self.provider == "openai":
                if not OPENAI_AVAILABLE or self.client is None:
                    return "Context extraction unavailable: OpenAI client not installed or API key not provided."
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant skilled in extracting important context from documents."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content
            elif self.provider == "gemini":
                if self.client == "direct_api":
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                        payload = {
                            "contents": [{
                                "parts": [{"text": prompt}]
                            }]
                        }
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(url, json=payload, headers=headers)
                        if response.status_code == 200:
                            data = response.json()
                            return data['candidates'][0]['content']['parts'][0]['text']
                        else:
                            logger.error(f"Gemini API request failed with status code {response.status_code}: {response.text}")
                            return ""
                    except Exception as e:
                        logger.error(f"Error generating text with Gemini: {e}")
                        return ""
                else:
                    return "Context extraction unavailable: Gemini client not initialized with direct API key."
            else:
                return "Context extraction unavailable: No valid LLM provider configured."
        except Exception as e:
            return f"Context extraction failed with {self.provider}: {str(e)}"

    def is_available(self) -> bool:
        """
        Check if the LLM client is available and properly initialized.
        
        Returns:
            bool: True if the client is available, False otherwise.
        """
        availability = hasattr(self, 'client') and self.client is not None
        logger.info(f"{self.__class__.__name__} availability check: {availability}")
        return availability

    def generate_content(self, prompt: str) -> str:
        """
        Generate content based on a given prompt using the configured LLM provider.
        
        This method sends the prompt to the selected LLM provider and returns the generated content.
        It handles provider-specific API calls and error conditions like quota limits.
        
        Args:
            prompt (str): The text prompt to generate content from.
        
        Returns:
            str: The generated content or an empty string if generation fails.
        
        Raises:
            Exception: For specific error conditions like Gemini API quota limits.
        """
        logger.info(f"Generating content with {self.provider} using model {self.model}")
        try:
            if self.provider == "ollama":
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                ).choices[0].message.content
            elif self.provider == "openai":
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                ).choices[0].message.content
            elif self.provider == "gemini":
                if self.client == "direct_api":
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                        payload = {
                            "contents": [{
                                "parts": [{"text": prompt}]
                            }]
                        }
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(url, json=payload, headers=headers)
                        if response.status_code == 200:
                            data = response.json()
                            return data['candidates'][0]['content']['parts'][0]['text']
                        else:
                            logger.error(f"Gemini API request failed with status code {response.status_code}: {response.text}")
                            return ""
                    except Exception as e:
                        logger.error(f"Error generating text with Gemini: {e}")
                        return ""
                else:
                    response = self.client.generate_content(prompt)
                    return response.text
        except Exception as e:
            if self.provider == "gemini" and "quota" in str(e).lower():
                logger.error(f"Gemini API quota exceeded: {e}")
                raise Exception("Gemini API quota exceeded. Please check your plan and billing details at https://ai.google.dev/gemini-api/docs/rate-limits")
            logger.error(f"Error generating content with {self.provider}: {e}")
            return ""

# Initialize the LLM client for use throughout the application
llm_client = LLMClient() 