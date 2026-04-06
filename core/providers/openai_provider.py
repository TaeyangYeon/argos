"""
OpenAI provider implementation for the Argos vision algorithm design system.

This module implements the OpenAI API client using raw HTTP requests
(not the openai SDK) for maximum control and minimal dependencies.
"""

import json
from typing import Any, Dict

import requests

from core.exceptions import AIProviderError
from config.constants import AI_TIMEOUT_SECONDS
from .base_provider import IAIProvider


class OpenAIProvider(IAIProvider):
    """
    OpenAI API provider implementation.
    
    Uses raw HTTP requests to communicate with the OpenAI Chat Completions API.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
            
        Raises:
            ValueError: If api_key is empty
        """
        super().__init__(api_key)
        self._model = model
        self._base_url = "https://api.openai.com/v1"
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "OpenAI"
    
    def analyze(self, prompt: str) -> str:
        """
        Send a prompt to OpenAI and return the response.
        
        Args:
            prompt: The text prompt to analyze
            
        Returns:
            Text response from OpenAI
            
        Raises:
            AIProviderError: On HTTP error, timeout, or API error
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1  # Low temperature for consistent responses
        }
        
        try:
            response = requests.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=AI_TIMEOUT_SECONDS
            )
            
            if response.status_code == 401:
                raise AIProviderError("Invalid API key")
            elif response.status_code == 429:
                raise AIProviderError("Rate limit exceeded")
            elif response.status_code != 200:
                error_msg = self._extract_error_message(response)
                raise AIProviderError(f"HTTP {response.status_code}: {error_msg}")
            
            response_data = response.json()
            
            if "error" in response_data:
                error_msg = response_data["error"].get("message", "Unknown error")
                raise AIProviderError(f"API error: {error_msg}")
            
            if "choices" not in response_data or not response_data["choices"]:
                raise AIProviderError("No response choices returned")
            
            content = response_data["choices"][0]["message"]["content"]
            
            if not content:
                raise AIProviderError("Empty response from API")
            
            return content.strip()
            
        except requests.exceptions.Timeout:
            raise AIProviderError("Request timeout")
        except requests.exceptions.ConnectionError:
            raise AIProviderError("Connection error")
        except requests.exceptions.RequestException as e:
            raise AIProviderError(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise AIProviderError("Invalid JSON response")
        except KeyError as e:
            raise AIProviderError(f"Missing expected field in response: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test connection to OpenAI API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.analyze("ping")
            return len(response) > 0
        except AIProviderError:
            return False
    
    def _extract_error_message(self, response: requests.Response) -> str:
        """
        Extract error message from response.
        
        Args:
            response: HTTP response object
            
        Returns:
            Error message string
        """
        try:
            error_data = response.json()
            if "error" in error_data:
                return error_data["error"].get("message", response.text[:100])
        except (json.JSONDecodeError, KeyError):
            pass
        
        return response.text[:100] if response.text else "Unknown error"