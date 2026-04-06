"""
Claude provider implementation for the Argos vision algorithm design system.

This module implements the Anthropic Claude API client using raw HTTP requests
for maximum control and minimal dependencies.
"""

import json
from typing import Any, Dict

import requests

from core.exceptions import AIProviderError
from config.constants import AI_TIMEOUT_SECONDS
from .base_provider import IAIProvider


class ClaudeProvider(IAIProvider):
    """
    Claude API provider implementation.
    
    Uses raw HTTP requests to communicate with the Anthropic Claude API.
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Claude provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-sonnet-4-20250514)
            
        Raises:
            ValueError: If api_key is empty
        """
        super().__init__(api_key)
        self._model = model
        self._base_url = "https://api.anthropic.com/v1"
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "Claude"
    
    def analyze(self, prompt: str) -> str:
        """
        Send a prompt to Claude and return the response.
        
        Args:
            prompt: The text prompt to analyze
            
        Returns:
            Text response from Claude
            
        Raises:
            AIProviderError: On HTTP error, timeout, or API error
        """
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        payload = {
            "model": self._model,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self._base_url}/messages",
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
            
            if "content" not in response_data or not response_data["content"]:
                raise AIProviderError("No content in response")
            
            # Claude returns content as a list of content blocks
            content_blocks = response_data["content"]
            if not isinstance(content_blocks, list) or len(content_blocks) == 0:
                raise AIProviderError("Invalid content format in response")
            
            # Extract text from the first content block
            first_block = content_blocks[0]
            if "text" not in first_block:
                raise AIProviderError("No text in content block")
            
            content = first_block["text"]
            
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
        Test connection to Claude API.
        
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