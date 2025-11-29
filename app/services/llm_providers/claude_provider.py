"""
Anthropic Claude LLM provider implementation.
"""
import logging
import os
from anthropic import Anthropic
from app.services.llm_providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude LLM provider."""
    
    def __init__(self, model_name: str = "claude-3-sonnet-20240229", api_key: str = None):
        """
        Initialize Claude provider.
        
        Args:
            model_name: The Claude model to use (default: claude-3-sonnet-20240229)
            api_key: The Anthropic API key (default: from environment variable)
        """
        super().__init__(model_name)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        
        if self.validate_credentials():
            self._initialize_client()
    
    def validate_credentials(self) -> bool:
        """Validate that the Anthropic API key is set."""
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not configured")
            return False
        return True
    
    def _initialize_client(self) -> None:
        """Initialize the Anthropic client."""
        try:
            self.client = Anthropic(api_key=self.api_key)
            logger.info(f"Claude provider initialized with model '{self.model_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize Claude provider: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Claude provider is available."""
        if not self.validate_credentials():
            return False
        
        if self.client is None:
            self._initialize_client()
        
        return self.client is not None
    
    def generate_content(self, prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        """
        Generate content using Claude.
        
        Args:
            prompt: The input prompt
            temperature: Temperature for response generation
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            LLMResponse: The response from Claude
            
        Raises:
            Exception: If content generation fails
        """
        if self.client is None:
            if not self.is_available():
                raise Exception("Claude provider is not available")
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return LLMResponse(text=response.content[0].text, model_name=self.model_name)
        except Exception as e:
            logger.error(f"Error generating content with Claude: {e}")
            raise
