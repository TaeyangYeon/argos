"""
Unit tests for the AI provider layer.

Tests all provider implementations, factory pattern, retry logic,
safe execution, and error handling using mocked HTTP responses.
"""

import json
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from core.exceptions import AIProviderError
from core.providers.base_provider import IAIProvider, ProviderInfo, ProviderStatus
from core.providers.claude_provider import ClaudeProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.openai_provider import OpenAIProvider
from core.providers.provider_factory import ProviderFactory


class TestProviderFactory:
    """Tests for the ProviderFactory class."""
    
    def test_provider_factory_creates_openai(self):
        """Test factory creates OpenAI provider correctly."""
        provider = ProviderFactory.create("openai", "test-key")
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.get_provider_name() == "OpenAI"
    
    def test_provider_factory_creates_claude(self):
        """Test factory creates Claude provider correctly."""
        provider = ProviderFactory.create("claude", "test-key")
        
        assert isinstance(provider, ClaudeProvider)
        assert provider.get_provider_name() == "Claude"
    
    def test_provider_factory_creates_gemini(self):
        """Test factory creates Gemini provider correctly."""
        provider = ProviderFactory.create("gemini", "test-key")
        
        assert isinstance(provider, GeminiProvider)
        assert provider.get_provider_name() == "Gemini"
    
    def test_provider_factory_invalid_name_raises_value_error(self):
        """Test factory raises ValueError for unknown provider names."""
        with pytest.raises(ValueError, match="Unknown provider 'invalid'"):
            ProviderFactory.create("invalid", "test-key")
    
    def test_get_available_providers_returns_three(self):
        """Test factory returns all three available providers."""
        providers = ProviderFactory.get_available_providers()
        
        assert len(providers) == 3
        assert "openai" in providers
        assert "claude" in providers
        assert "gemini" in providers


class TestProviderDataStructures:
    """Tests for provider data classes and enums."""
    
    def test_provider_status_enum_values(self):
        """Test ProviderStatus enum has correct values."""
        assert ProviderStatus.CONNECTED.value == "connected"
        assert ProviderStatus.DISCONNECTED.value == "disconnected"
        assert ProviderStatus.ERROR.value == "error"
    
    def test_provider_info_dataclass_defaults(self):
        """Test ProviderInfo dataclass with default values."""
        info = ProviderInfo(
            provider_name="TestProvider",
            status=ProviderStatus.CONNECTED
        )
        
        assert info.provider_name == "TestProvider"
        assert info.status == ProviderStatus.CONNECTED
        assert info.model_version is None
        assert info.last_tested is None
    
    def test_provider_info_dataclass_with_values(self):
        """Test ProviderInfo dataclass with all values set."""
        info = ProviderInfo(
            provider_name="TestProvider",
            status=ProviderStatus.CONNECTED,
            model_version="1.0",
            last_tested="2026-04-06T10:00:00Z"
        )
        
        assert info.provider_name == "TestProvider"
        assert info.status == ProviderStatus.CONNECTED
        assert info.model_version == "1.0"
        assert info.last_tested == "2026-04-06T10:00:00Z"


class TestBaseProviderFunctionality:
    """Tests for base provider retry and safe execution functionality."""
    
    def create_mock_provider(self) -> IAIProvider:
        """Create a mock provider for testing."""
        class MockProvider(IAIProvider):
            def get_provider_name(self) -> str:
                return "Mock"
            
            def analyze(self, prompt: str) -> str:
                return "mock response"
            
            def test_connection(self) -> bool:
                return True
        
        return MockProvider("test-key")
    
    def test_empty_api_key_raises_value_error(self):
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="API key must not be empty"):
            self.create_mock_provider().__class__("")
        
        with pytest.raises(ValueError, match="API key must not be empty"):
            self.create_mock_provider().__class__("   ")
    
    @patch('time.sleep')
    def test_analyze_with_retry_succeeds_on_first_try(self, mock_sleep):
        """Test analyze_with_retry succeeds without retries."""
        provider = self.create_mock_provider()
        
        # Mock analyze to return success
        provider.analyze = Mock(return_value="success")
        
        result = provider.analyze_with_retry("test prompt")
        
        assert result == "success"
        provider.analyze.assert_called_once_with("test prompt")
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    def test_analyze_with_retry_retries_on_failure(self, mock_sleep):
        """Test analyze_with_retry retries on failure and eventually succeeds."""
        provider = self.create_mock_provider()
        
        # Mock analyze to fail twice then succeed
        provider.analyze = Mock(side_effect=[
            AIProviderError("Error 1"),
            AIProviderError("Error 2"),
            "success"
        ])
        
        result = provider.analyze_with_retry("test prompt")
        
        assert result == "success"
        assert provider.analyze.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(2)  # Should wait 2 seconds
    
    @patch('time.sleep')
    def test_analyze_with_retry_fails_after_all_retries(self, mock_sleep):
        """Test analyze_with_retry fails after exhausting all retries."""
        provider = self.create_mock_provider()
        
        # Mock analyze to always fail
        provider.analyze = Mock(side_effect=AIProviderError("Always fails"))
        
        with pytest.raises(AIProviderError, match="Failed after 3 attempts"):
            provider.analyze_with_retry("test prompt")
        
        # Should try 3 times total (initial + 2 retries)
        assert provider.analyze.call_count == 3
        assert mock_sleep.call_count == 2
    
    def test_analyze_safe_returns_fallback_on_all_failures(self):
        """Test analyze_safe returns fallback and never raises."""
        provider = self.create_mock_provider()
        
        # Mock analyze_with_retry to always fail
        provider.analyze_with_retry = Mock(side_effect=AIProviderError("Always fails"))
        
        result = provider.analyze_safe("test prompt", fallback="fallback_value")
        
        assert result == "fallback_value"
        provider.analyze_with_retry.assert_called_once_with("test prompt")
    
    def test_analyze_safe_returns_response_on_success(self):
        """Test analyze_safe returns actual response when successful."""
        provider = self.create_mock_provider()
        
        # Mock analyze_with_retry to succeed
        provider.analyze_with_retry = Mock(return_value="success")
        
        result = provider.analyze_safe("test prompt", fallback="fallback")
        
        assert result == "success"
        provider.analyze_with_retry.assert_called_once_with("test prompt")


class TestOpenAIProvider:
    """Tests for OpenAI provider implementation."""
    
    @patch('requests.post')
    def test_openai_successful_response(self, mock_post):
        """Test OpenAI provider with successful response."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "OpenAI response"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        provider = OpenAIProvider("test-key")
        result = provider.analyze("test prompt")
        
        assert result == "OpenAI response"
        mock_post.assert_called_once()
        
        # Verify correct URL and headers
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"
    
    @patch('requests.post')
    def test_openai_api_error_response(self, mock_post):
        """Test OpenAI provider with API error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Error response text"
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid request"
            }
        }
        mock_post.return_value = mock_response
        
        provider = OpenAIProvider("test-key")
        
        with pytest.raises(AIProviderError, match="HTTP 400: Invalid request"):
            provider.analyze("test prompt")
    
    @patch('requests.post')
    def test_openai_timeout_error(self, mock_post):
        """Test OpenAI provider with timeout error."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        provider = OpenAIProvider("test-key")
        
        with pytest.raises(AIProviderError, match="Request timeout"):
            provider.analyze("test prompt")
    
    @patch('requests.post')
    def test_openai_test_connection_success(self, mock_post):
        """Test OpenAI test_connection with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "pong"}}]
        }
        mock_post.return_value = mock_response
        
        provider = OpenAIProvider("test-key")
        result = provider.test_connection()
        
        assert result is True
    
    @patch('requests.post')
    def test_openai_test_connection_failure(self, mock_post):
        """Test OpenAI test_connection with failure."""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        provider = OpenAIProvider("test-key")
        result = provider.test_connection()
        
        assert result is False


class TestClaudeProvider:
    """Tests for Claude provider implementation."""
    
    @patch('requests.post')
    def test_claude_successful_response(self, mock_post):
        """Test Claude provider with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "text": "Claude response"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        provider = ClaudeProvider("test-key")
        result = provider.analyze("test prompt")
        
        assert result == "Claude response"
        mock_post.assert_called_once()
        
        # Verify correct URL and headers
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.anthropic.com/v1/messages"
        assert call_args[1]["headers"]["x-api-key"] == "test-key"
    
    @patch('requests.post')
    def test_claude_test_connection_success(self, mock_post):
        """Test Claude test_connection with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "pong"}]
        }
        mock_post.return_value = mock_response
        
        provider = ClaudeProvider("test-key")
        result = provider.test_connection()
        
        assert result is True


class TestGeminiProvider:
    """Tests for Gemini provider implementation."""
    
    @patch('requests.post')
    def test_gemini_successful_response(self, mock_post):
        """Test Gemini provider with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Gemini response"
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        provider = GeminiProvider("test-key")
        result = provider.analyze("test prompt")
        
        assert result == "Gemini response"
        mock_post.assert_called_once()
        
        # Verify correct URL
        call_args = mock_post.call_args
        expected_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
        assert call_args[0][0] == expected_url
    
    @patch('requests.post')
    def test_gemini_test_connection_success(self, mock_post):
        """Test Gemini test_connection with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "pong"}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        provider = GeminiProvider("test-key")
        result = provider.test_connection()
        
        assert result is True