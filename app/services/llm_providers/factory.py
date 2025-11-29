"""
LLM Provider Factory with fallback support.
Manages provider initialization, selection, and automatic fallback logic.
"""
import logging
import time
from typing import List, Optional, Tuple
from app.services.llm_providers.base import LLMProvider, LLMResponse
from app.services.llm_providers.gemini_provider import GeminiProvider
from app.services.llm_providers.claude_provider import ClaudeProvider
from app.config import Config

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for managing LLM providers with fallback support."""
    
    # Provider registry
    PROVIDER_REGISTRY = {
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
    }
    
    def __init__(self, primary_provider: str = None, fallback_providers: List[str] = None):
        """
        Initialize the LLM factory.
        
        Args:
            primary_provider: The primary LLM provider to use (default: from config)
            fallback_providers: List of fallback providers in priority order
                               (default: from config)
        """
        self.primary_provider_name = primary_provider or Config.LLM_PRIMARY_PROVIDER
        self.fallback_provider_names = fallback_providers or Config.LLM_FALLBACK_PROVIDERS
        
        self.current_provider: Optional[LLMProvider] = None
        self.primary_provider: Optional[LLMProvider] = None
        self.fallback_providers: List[Tuple[str, LLMProvider]] = []
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize primary and fallback providers."""
        # Initialize primary provider
        self.primary_provider = self._create_provider(self.primary_provider_name)
        if self.primary_provider and self.primary_provider.is_available():
            self.current_provider = self.primary_provider
            logger.info(f"Primary provider '{self.primary_provider_name}' is available and set as current")
        else:
            logger.warning(f"Primary provider '{self.primary_provider_name}' is not available")
        
        # Initialize fallback providers
        for provider_name in self.fallback_provider_names:
            provider = self._create_provider(provider_name)
            if provider:
                self.fallback_providers.append((provider_name, provider))
                logger.info(f"Fallback provider '{provider_name}' initialized")
        
        # If primary is not available, use first available fallback
        if self.current_provider is None:
            self._switch_to_fallback()
    
    def _create_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """
        Create a provider instance.
        
        Args:
            provider_name: The name of the provider to create
            
        Returns:
            LLMProvider instance or None if provider cannot be created
        """
        provider_name = provider_name.lower()
        
        if provider_name not in self.PROVIDER_REGISTRY:
            logger.error(f"Unknown provider: {provider_name}")
            return None
        
        try:
            provider_class = self.PROVIDER_REGISTRY[provider_name]
            provider = provider_class()
            return provider
        except Exception as e:
            logger.error(f"Failed to create provider '{provider_name}': {e}")
            return None
    
    def _switch_to_fallback(self) -> bool:
        """
        Switch to the next available fallback provider.
        
        Returns:
            bool: True if a fallback provider was found and set, False otherwise
        """
        for provider_name, provider in self.fallback_providers:
            if provider.is_available():
                self.current_provider = provider
                logger.warning(f"Switched to fallback provider: {provider_name}")
                return True
        
        logger.error("No fallback providers available")
        return False
    
    def _handle_provider_error(self, error: Exception, is_quota_error: bool = False) -> bool:
        """
        Handle provider errors and attempt fallback.
        
        Args:
            error: The exception that occurred
            is_quota_error: Whether this is a quota/rate limit error
            
        Returns:
            bool: True if fallback was successful, False otherwise
        """
        if is_quota_error:
            logger.warning(f"Quota/rate limit error from {self.current_provider.get_provider_name()}: {error}")
        else:
            logger.error(f"Error from {self.current_provider.get_provider_name()}: {error}")
        
        return self._switch_to_fallback()
    
    def _is_quota_error(self, error: Exception) -> bool:
        """
        Check if the error is a quota or rate limit error.
        
        Args:
            error: The exception to check
            
        Returns:
            bool: True if this is a quota/rate limit error
        """
        error_str = str(error).lower()
        quota_indicators = ["429", "quota exceeded", "rate limit", "too many requests"]
        return any(indicator in error_str for indicator in quota_indicators)
    
    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        max_retries: int = 5,
        retry_delay: int = 5
    ) -> LLMResponse:
        """
        Generate content using the current provider with retry and fallback logic.
        
        Args:
            prompt: The input prompt
            temperature: Temperature for response generation
            max_tokens: Maximum number of tokens
            max_retries: Maximum number of retries for rate limit errors
            retry_delay: Delay between retries in seconds
            
        Returns:
            LLMResponse: The response from the LLM
            
        Raises:
            Exception: If no provider can generate content
        """
        if self.current_provider is None:
            raise Exception("No LLM provider available")
        
        retry_count = 0
        base_delay = retry_delay
        
        while True:
            try:
                response = self.current_provider.generate_content(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                logger.debug(f"Successfully generated content using {self.current_provider.get_provider_name()}")
                return response
            
            except Exception as e:
                is_quota = self._is_quota_error(e)
                
                if is_quota and retry_count < max_retries:
                    # Rate limit error - retry with backoff
                    delay = base_delay * (2 ** retry_count)
                    retry_count += 1
                    logger.warning(
                        f"Rate limit error (attempt {retry_count}/{max_retries}). "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                    continue
                
                # Try fallback provider
                if self._handle_provider_error(e, is_quota):
                    # Reset retry count for new provider
                    retry_count = 0
                    base_delay = retry_delay
                    continue
                
                # No fallback available
                raise Exception(
                    f"All LLM providers exhausted. Last error: {e}"
                )
    
    def get_current_provider(self) -> Optional[LLMProvider]:
        """
        Get the current active provider.
        
        Returns:
            LLMProvider: The currently active provider or None
        """
        return self.current_provider
    
    def get_provider_status(self) -> dict:
        """
        Get the status of all providers.
        
        Returns:
            dict: Status information for all providers
        """
        status = {
            "current_provider": self.current_provider.get_provider_name() if self.current_provider else "None",
            "primary": {
                "name": self.primary_provider_name,
                "available": self.primary_provider.is_available() if self.primary_provider else False,
            },
            "fallbacks": []
        }
        
        for name, provider in self.fallback_providers:
            status["fallbacks"].append({
                "name": name,
                "available": provider.is_available(),
            })
        
        return status
    
    def register_provider(self, provider_name: str, provider_class) -> None:
        """
        Register a custom provider class.
        
        Args:
            provider_name: The name to register the provider under
            provider_class: The provider class (must inherit from LLMProvider)
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError("Provider class must inherit from LLMProvider")
        
        self.PROVIDER_REGISTRY[provider_name.lower()] = provider_class
        logger.info(f"Registered custom provider: {provider_name}")
