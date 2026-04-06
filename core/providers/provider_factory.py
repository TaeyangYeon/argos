"""
Provider factory for the Argos vision algorithm design system.

This module implements the factory pattern for creating AI provider instances
based on provider names, supporting dynamic provider selection at runtime.
"""

from typing import List

from .base_provider import IAIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


class ProviderFactory:
    """
    Factory class for creating AI provider instances.
    
    Implements the factory pattern to abstract provider creation
    and support dynamic provider selection.
    """
    
    # Mapping of provider names to their implementation classes
    _PROVIDERS = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
    }
    
    @classmethod
    def create(cls, provider_name: str, api_key: str) -> IAIProvider:
        """
        Create an AI provider instance.
        
        Args:
            provider_name: Name of the provider ("openai", "claude", "gemini")
            api_key: API key for the provider
            
        Returns:
            IAIProvider instance for the specified provider
            
        Raises:
            ValueError: If provider_name is not supported
        """
        provider_name_lower = provider_name.lower()
        
        if provider_name_lower not in cls._PROVIDERS:
            available = ", ".join(cls._PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._PROVIDERS[provider_name_lower]
        return provider_class(api_key)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get list of available provider names.
        
        Returns:
            List of supported provider names
        """
        return list(cls._PROVIDERS.keys())