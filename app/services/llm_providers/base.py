"""
Abstract base class for LLM providers.
Defines the interface that all LLM implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Optional


class LLMResponse:
    """Wrapper class for LLM responses to provide a consistent interface."""
    
    def __init__(self, text: str, model_name: str):
        """
        Initialize LLM response.
        
        Args:
            text: The response text from the LLM
            model_name: The name of the model that generated this response
        """
        self.text = text
        self.model_name = model_name


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, model_name: str):
        """
        Initialize the LLM provider.
        
        Args:
            model_name: The name of the model to use
        """
        self.model_name = model_name
    
    @abstractmethod
    def generate_content(self, prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        """
        Generate content using the LLM.
        
        Args:
            prompt: The input prompt for the LLM
            temperature: Temperature for response generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            LLMResponse: The response from the LLM
            
        Raises:
            Exception: If there's an error generating content
        """
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate that the provider has valid credentials and API keys.
        
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available (credentials valid and API accessible).
        
        Returns:
            bool: True if the provider is available, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.
        
        Returns:
            str: The provider name
        """
        return self.__class__.__name__
