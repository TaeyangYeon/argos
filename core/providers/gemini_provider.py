"""
Gemini provider implementation for the Argos vision algorithm design system.

This module implements the Google Gemini API client using raw HTTP requests
for maximum control and minimal dependencies.
"""

import json
from typing import Any, Dict

import requests

from core.exceptions import AIProviderError
from config.constants import AI_TIMEOUT_SECONDS
from .base_provider import IAIProvider


class GeminiProvider(IAIProvider):
    """
    Google Gemini API provider implementation.
    
    Uses raw HTTP requests to communicate with the Google Generative Language API.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            model: Model to use (default: gemini-1.5-pro)
            
        Raises:
            ValueError: If api_key is empty
        """
        super().__init__(api_key)
        self._model = model
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "Gemini"
    
    def analyze(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the response.
        
        Args:
            prompt: The text prompt to analyze
            
        Returns:
            Text response from Gemini
            
        Raises:
            AIProviderError: On HTTP error, timeout, or API error
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistent responses
                "maxOutputTokens": 1000
            }
        }
        
        try:
            url = f"{self._base_url}/models/{self._model}:generateContent"
            params = {"key": self._api_key}
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                params=params,
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
            
            if "candidates" not in response_data or not response_data["candidates"]:
                raise AIProviderError("No candidates in response")
            
            # Extract content from the first candidate
            candidate = response_data["candidates"][0]
            
            if "content" not in candidate:
                raise AIProviderError("No content in candidate")
            
            content_parts = candidate["content"].get("parts", [])
            if not content_parts:
                raise AIProviderError("No parts in content")
            
            # Extract text from the first part
            first_part = content_parts[0]
            if "text" not in first_part:
                raise AIProviderError("No text in content part")
            
            content = first_part["text"]
            
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
        Test connection to Gemini API.
        
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