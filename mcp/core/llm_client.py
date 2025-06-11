import logging
from typing import Optional
import google.generativeai as genai
from .config import Settings

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_agent.log")
    ]
)

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
    
    def extract_context(self, text: str, max_length: int = 500) -> str:
        """Extract key context and points from the provided text."""
        if not self.is_available():
            logger.warning("Context extraction unavailable: Client not configured")
            return "Context extraction unavailable: Client not configured"
        
        prompt = f"""
        Extract the most important context and key points from the following text.
        Focus on main ideas, critical information, and essential details.
        Keep the summary concise, within {max_length} characters.
        
        Text: {text}
        
        Format the response with clear sections and use **bold** for important terms.
        """
        return self.generate_content(prompt)
    
    def summarize_text(self, text: str, max_length: int = 1000) -> str:
        """Summarize the provided text with key details and recommendations."""
        if not self.is_available():
            logger.warning("Summarization unavailable: Client not configured")
            return "Summarization unavailable: Client not configured"
        
        prompt = f"""
        Create a comprehensive summary of the following text.
        Include:
        1. Main topic and purpose
        2. Key points and findings
        3. Important context and background
        4. Critical information
        5. Recommendations or action items
        
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
            return ""
        
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