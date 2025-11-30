"""
Google Gemini LLM provider implementation.
"""
import logging
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False
from app.services.llm_providers.base import LLMProvider, LLMResponse
from app.config import Config

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""
    
    def __init__(self, model_name: str = None, api_key: str = None):
        """
        Initialize Gemini provider.
        
        Args:
            model_name: The Gemini model to use (default: from config)
            api_key: The Google API key (default: from config)
        """
        model_name = model_name or Config.CHAT_MODEL
        super().__init__(model_name)
        self.api_key = api_key or Config.GOOGLE_API_KEY
        self.model = None
        
        if self.validate_credentials():
            self._initialize_model()
    
    def validate_credentials(self) -> bool:
        """Validate that the Google API key is set and module is available."""
        if not GENAI_AVAILABLE:
            logger.error("google-generativeai module not installed. Install with 'pip install google-generativeai'")
            return False
            
        if not self.api_key:
            logger.error("GOOGLE_API_KEY not configured")
            return False
        return True
    
    def _initialize_model(self) -> None:
        """Initialize the Gemini model."""
        if not GENAI_AVAILABLE:
            return
            
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini model '{self.model_name}' initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Gemini provider is available."""
        if not self.validate_credentials():
            return False
        
        if self.model is None:
            self._initialize_model()
        
        return self.model is not None
    
    def generate_content(self, prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        """
        Generate content using Gemini.
        
        Args:
            prompt: The input prompt
            temperature: Temperature for response generation
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            LLMResponse: The response from Gemini
            
        Raises:
            Exception: If content generation fails
        """
        if self.model is None:
            if not self.is_available():
                raise Exception("Gemini provider is not available")
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            return LLMResponse(text=response.text, model_name=self.model_name)
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            raise
