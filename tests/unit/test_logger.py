"""
Unit tests for the logging system.

Tests the ArgosLogger singleton pattern, logger creation, file handling,
exception logging integration, and error handler functionality.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.logger import ArgosLogger, get_logger, LogLevel
from core.exceptions import (
    InputValidationError, 
    RuntimeProcessingError, 
    OutputValidationError, 
    AIProviderError
)
from core.error_handler import handle_input_error, handle_runtime_error, safe_execute


class TestArgosLogger:
    """Tests for the ArgosLogger singleton class."""
    
    def setup_method(self):
        """Reset the singleton for each test."""
        ArgosLogger._instance = None
        ArgosLogger._initialized = False
    
    def test_logger_singleton(self):
        """Test that ArgosLogger follows singleton pattern."""
        logger1 = ArgosLogger()
        logger2 = ArgosLogger()
        
        assert logger1 is logger2
        assert id(logger1) == id(logger2)
    
    @patch('core.logger.LOGS_DIR')
    def test_logger_creates_log_dir(self, mock_logs_dir):
        """Test that ArgosLogger creates the logs directory."""
        mock_logs_dir.mkdir = MagicMock()
        
        ArgosLogger()
        
        mock_logs_dir.mkdir.assert_called_once_with(exist_ok=True)
    
    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logging.Logger instance."""
        logger_manager = ArgosLogger()
        logger = logger_manager.get("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "argos.test_module"
    
    def test_log_file_created(self):
        """Test that logging actually creates a log file."""
        from config.paths import LOGS_DIR
        
        # Get a logger and log a message
        logger = get_logger("test")
        logger.info("Test message")
        
        # Check if any log file was created in logs directory
        log_files = list(LOGS_DIR.glob("*.log"))
        assert len(log_files) > 0, "No log file was created"
        
        # Clean up the test log file after test
        for log_file in log_files:
            if log_file.name.startswith("argos_"):
                # Just verify it exists, don't delete it as other tests may use it
                assert log_file.stat().st_size > 0, "Log file is empty"
                break
    
    def test_set_level(self):
        """Test that set_level changes logging levels correctly."""
        logger_manager = ArgosLogger()
        
        logger_manager.set_level(LogLevel.ERROR)
        
        # Test that the root logger level is set correctly
        root_logger = logging.getLogger("argos")
        assert root_logger.level == LogLevel.ERROR.value
    
    def test_disable_console(self):
        """Test that disable_console method works correctly."""
        logger_manager = ArgosLogger()
        
        # Ensure console handler exists by adding it
        if not hasattr(logger_manager, '_console_handler'):
            logger_manager._add_console_handler()
        
        # Verify console handler is in handlers list
        assert hasattr(logger_manager, '_console_handler')
        assert logger_manager._console_handler in logger_manager._root_logger.handlers
        
        initial_handler_count = len(logger_manager._root_logger.handlers)
        
        # Call disable_console
        logger_manager.disable_console()
        
        # Verify the console handler is no longer in the handlers list
        final_handler_count = len(logger_manager._root_logger.handlers)
        assert logger_manager._console_handler not in logger_manager._root_logger.handlers
        assert final_handler_count == initial_handler_count - 1


class TestGetLoggerFunction:
    """Tests for the get_logger convenience function."""
    
    def setup_method(self):
        """Reset the singleton for each test."""
        ArgosLogger._instance = None
        ArgosLogger._initialized = False
    
    def test_get_logger_convenience_function(self):
        """Test that get_logger function works correctly."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "argos.test_module"


class TestExceptionLogging:
    """Tests for exception raise_with_log classmethods."""
    
    def setup_method(self):
        """Reset the singleton for each test."""
        ArgosLogger._instance = None
        ArgosLogger._initialized = False
    
    def test_raise_with_log_input_error(self, caplog):
        """Test InputValidationError.raise_with_log logs and raises."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(InputValidationError, match="Test input error"):
                InputValidationError.raise_with_log("Test input error", logger)
        
        assert "Input validation error: Test input error" in caplog.text
    
    def test_raise_with_log_runtime_error(self, caplog):
        """Test RuntimeProcessingError.raise_with_log logs and raises."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeProcessingError, match="Test runtime error"):
                RuntimeProcessingError.raise_with_log("Test runtime error", logger)
        
        assert "Runtime processing error: Test runtime error" in caplog.text
    
    def test_raise_with_log_output_error(self, caplog):
        """Test OutputValidationError.raise_with_log logs and raises."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(OutputValidationError, match="Test output error"):
                OutputValidationError.raise_with_log("Test output error", logger)
        
        assert "Output validation error: Test output error" in caplog.text
    
    def test_raise_with_log_ai_provider_error(self, caplog):
        """Test AIProviderError.raise_with_log logs and raises."""
        logger = get_logger("test")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(AIProviderError, match="Test AI error"):
                AIProviderError.raise_with_log("Test AI error", logger)
        
        assert "AI provider error: Test AI error" in caplog.text


class TestErrorHandlers:
    """Tests for error handler decorators and safe_execute function."""
    
    def setup_method(self):
        """Reset the singleton for each test."""
        ArgosLogger._instance = None
        ArgosLogger._initialized = False
    
    def test_handle_input_error_decorator(self, caplog):
        """Test handle_input_error decorator logs and re-raises."""
        @handle_input_error
        def failing_function():
            raise InputValidationError("Test error")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(InputValidationError):
                failing_function()
        
        assert "Input validation failed in failing_function: Test error" in caplog.text
    
    def test_handle_runtime_error_decorator(self, caplog):
        """Test handle_runtime_error decorator logs and re-raises."""
        @handle_runtime_error
        def failing_function():
            raise RuntimeProcessingError("Test error")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeProcessingError):
                failing_function()
        
        assert "Runtime processing failed in failing_function: Test error" in caplog.text
    
    def test_safe_execute_success(self):
        """Test safe_execute returns function result on success."""
        def successful_function(x, y):
            return x + y
        
        result = safe_execute(successful_function, 2, 3)
        
        assert result == 5
    
    def test_safe_execute_failure(self, caplog):
        """Test safe_execute returns fallback value on exception and doesn't raise."""
        def failing_function():
            raise ValueError("Test error")
        
        with caplog.at_level(logging.ERROR):
            result = safe_execute(failing_function, fallback="fallback_value")
        
        assert result == "fallback_value"
        assert "Function failing_function failed: Test error" in caplog.text
    
    def test_safe_execute_with_custom_logger(self, caplog):
        """Test safe_execute with custom logger."""
        custom_logger = get_logger("custom")
        
        def failing_function():
            raise ValueError("Custom error")
        
        with caplog.at_level(logging.ERROR):
            result = safe_execute(failing_function, fallback=None, logger=custom_logger)
        
        assert result is None
        assert "Function failing_function failed: Custom error" in caplog.text