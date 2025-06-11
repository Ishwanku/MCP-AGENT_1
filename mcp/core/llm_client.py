import logging
from typing import List
from .config import Settings
import google.generativeai as genai

# Logger setup (assumes logging is configured in config.py or a dedicated module)
logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with large language models, currently supporting Gemini."""
    
    def __init__(self, settings: Settings):
        """Initialize the LLM client with the provided settings."""
        self.provider = settings.LLM_PROVIDER
        self.client = None
        self.model = settings.GEMINI_MODEL
        self._init_client(settings)
    
    def _init_client(self, settings: Settings):
        """Initialize the LLM client based on the provider."""
        valid_providers = ["gemini"]
        if self.provider not in valid_providers:
            logger.error(f"Invalid LLM_PROVIDER: {self.provider}. Must be one of {valid_providers}")
            raise ValueError(f"Invalid LLM_PROVIDER: {self.provider}. Must be one of {valid_providers}")
        
        if self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY not provided in settings")
                raise ValueError("GEMINI_API_KEY is required for Gemini provider")
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.client = genai.GenerativeModel(settings.GEMINI_MODEL)
                logger.info(f"Initialized Gemini client with model {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise
    
    def generate_summary(self, text: str, max_length: int = 1000, sections: List[str] = None) -> str:
        """Generate a summary of the provided text with specified sections and length."""
        if not self.is_available():
            logger.warning("Content generation unavailable: Client not configured")
            return "Content generation unavailable: Client not configured"
        
        sections = sections or ["main topic", "key points", "context", "recommendations"]
        prompt = f"""
        Summarize the following text.
        Include: {', '.join(sections)}
        Keep the summary within {max_length} characters.
        Text: {text}
        Format the response with clear sections and use **bold** for important terms.
        """
        return self.generate_content(prompt)
    
    def is_available(self) -> bool:
        """Check if the LLM client is available and properly initialized."""
        availability = hasattr(self, 'client') and self.client is not None
        logger.debug(f"LLMClient availability check: {availability}")
        return availability
    
    def generate_content(self, prompt: str) -> str:
        """Generate content using the configured LLM provider."""
        if not self.is_available():
            logger.warning("Content generation unavailable: Client not configured")
            return "Content generation unavailable: Client not configured"
        
        logger.info(f"Generating content with {self.provider} using model {self.model}")
        try:
            response = self.client.generate_content(prompt)
            logger.debug("Content generated successfully")
            return response.text
        except Exception as e:
            if "quota" in str(e).lower():
                logger.error(f"Gemini API quota exceeded: {e}")
                raise Exception("Gemini API quota exceeded. Please check your plan and billing details at https://ai.google.dev/gemini-api/docs/rate-limits")
            logger.error(f"Error generating content: {e}")
            return f"Error generating content: {str(e)}"