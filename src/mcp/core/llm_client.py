import logging
from typing import List, Dict, Any, Optional
from .config import Settings
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion
from .utils import retry_llm_call

# Logger setup (assumes logging is configured in config.py or a dedicated module)
logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with large language models via Azure AI Foundry."""
    
    # Add support for LLM ( REads config file, Set's Properties and initialize the client)
    def __init__(self, settings: Settings):
        """Initialize the LLM client with the provided settings."""
        self.provider = settings.LLM_PROVIDER
        self.client = None
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        self.content_safety_enabled = settings.CONTENT_SAFETY_ENABLED
        self.content_safety_threshold = settings.CONTENT_SAFETY_THRESHOLD
        self._init_client(settings)
    
    # Initialize the LLM client based on the provider
    def _init_client(self, settings: Settings):
        """Initialize the LLM client based on the provider."""
        valid_providers = ["azure"]
        if self.provider not in valid_providers:
            logger.error(f"Invalid LLM_PROVIDER: {self.provider}. Must be one of {valid_providers}")
            raise ValueError(f"Invalid LLM_PROVIDER: {self.provider}. Must be one of {valid_providers}")
        
        if self.provider == "azure":
            if not settings.AZURE_OPENAI_API_KEY:
                logger.error("AZURE_OPENAI_API_KEY not provided in settings")
                raise ValueError("AZURE_OPENAI_API_KEY is required for Azure OpenAI provider")
            if not settings.AZURE_OPENAI_ENDPOINT:
                logger.error("AZURE_OPENAI_ENDPOINT not provided in settings")
                raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI provider")
            if not settings.AZURE_OPENAI_DEPLOYMENT_NAME:
                logger.error("AZURE_OPENAI_DEPLOYMENT_NAME not provided in settings")
                raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME is required for Azure OpenAI provider")
            
            try:
                self.client = AzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
                logger.info(f"Initialized Azure OpenAI client with deployment {self.deployment_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI client: {e}")
                raise
    
    # Check if content meets safety thresholds
    def _check_content_safety(self, text: str) -> bool:
        """Check if content meets safety thresholds."""
        if not self.content_safety_enabled:
            return True
            
        try:
            # Implement content safety check using Azure AI Content Safety
            # This is a placeholder - you'll need to implement the actual content safety check
            return True
        except Exception as e:
            logger.warning(f"Content safety check failed: {e}")
            return True
    
    # 7 Generate a summary of the provided text with specified sections(gives the prompt text to the LLM)
    def generate_summary(self, text: str, max_length: int = 1000, sections: List[str] = None) -> str:
        """Generate a summary of the provided text with specified sections and length."""
        if not self.is_available():
            logger.warning("Content generation unavailable: Client not configured")
            return "Content generation unavailable: Client not configured"
        
        if not self._check_content_safety(text):
            return "Content safety check failed. Please review the input text."
        
        sections = sections or ["main topic", "key points", "context", "recommendations"]
        prompt = f"""
        Summarize the following text.
        Include: {', '.join(sections)}
        Keep the summary within {max_length} characters.
        Text: {text}
        Format the response with clear sections and use **bold** for important terms.
        """
        return self.generate_content(prompt)
    
    # Check if the LLM client is available
    def is_available(self) -> bool:
        """Check if the LLM client is available and properly initialized."""
        availability = hasattr(self, 'client') and self.client is not None
        logger.debug(f"LLMClient availability check: {availability}")
        return availability
    
    @retry_llm_call(
        max_attempts=3,
        initial_wait=1.0,
        max_wait=10.0,
        exceptions=(Exception,)
    )
    async def generate_content(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate content using Azure OpenAI with retry mechanism.
        
        Args:
            prompt (str): The prompt to send to the LLM
            max_tokens (int): Maximum number of tokens to generate
            temperature (float): Temperature for response generation
            
        Returns:
            str: Generated content
        """
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes documents and provides concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if not response.choices:
                logger.warning("No response generated from LLM")
                return "No response generated"
                
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise