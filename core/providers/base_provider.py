"""
Base AI provider interface and utilities for the Argos vision algorithm design system.

This module defines the abstract base class for all AI providers, common data structures,
and utility methods for retry logic and safe execution.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from core.exceptions import AIProviderError
from core.logger import get_logger
from config.constants import AI_RETRY_COUNT


class ProviderStatus(Enum):
    """Status of an AI provider connection."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ProviderInfo:
    """Information about an AI provider."""
    provider_name: str
    status: ProviderStatus
    model_version: Optional[str] = None
    last_tested: Optional[str] = None  # ISO datetime string


class IAIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    Defines the interface that all AI providers must implement,
    including abstract methods for core functionality and concrete
    methods for retry logic and safe execution.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the AI provider.
        
        Args:
            api_key: API key for the provider
            
        Raises:
            ValueError: If api_key is empty
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty")
        
        # SECURITY: never log api_key
        self._api_key = api_key
        self._logger = get_logger(f"providers.{self.get_provider_name().lower()}")
    
    @abstractmethod
    def analyze(self, prompt: str) -> str:
        """
        Send a text prompt and return text response.
        
        Args:
            prompt: The text prompt to analyze
            
        Returns:
            Text response from the AI provider
            
        Raises:
            AIProviderError: On communication or API errors
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the provider.
        
        Returns:
            Provider name (e.g., "OpenAI", "Claude", "Gemini")
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the API key is valid and the provider is reachable.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    def analyze_with_retry(self, prompt: str) -> str:
        """
        Analyze with automatic retry on failure.
        
        Calls analyze() up to AI_RETRY_COUNT times with 2 second delays
        between retries.
        
        Args:
            prompt: The text prompt to analyze
            
        Returns:
            Text response from the AI provider
            
        Raises:
            AIProviderError: If all retries fail
        """
        last_error = None
        
        for attempt in range(AI_RETRY_COUNT + 1):  # +1 for initial attempt
            try:
                if attempt > 0:
                    self._logger.info(f"Retrying AI call, attempt {attempt + 1}")
                    time.sleep(2)  # Wait exactly 2 seconds between retries
                
                return self.analyze(prompt)
                
            except AIProviderError as e:
                last_error = e
                self._logger.warning(f"AI call failed on attempt {attempt + 1}: {e}")
                
                if attempt == AI_RETRY_COUNT:  # Last attempt
                    break
        
        # All retries failed
        self._logger.error(f"All {AI_RETRY_COUNT + 1} attempts failed for {self.get_provider_name()}")
        raise AIProviderError(f"Failed after {AI_RETRY_COUNT + 1} attempts: {last_error}")
    
    def analyze_safe(self, prompt: str, fallback: str = "") -> str:
        """
        Safe analysis that never raises exceptions.
        
        Calls analyze_with_retry() and returns fallback on any error.
        
        Args:
            prompt: The text prompt to analyze
            fallback: Fallback string to return on error
            
        Returns:
            AI response on success, fallback string on any error
        """
        try:
            return self.analyze_with_retry(prompt)
        except AIProviderError as e:
            self._logger.warning(f"AI analysis failed, returning fallback: {e}")
            return fallback