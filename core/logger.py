"""
Logging system for the Argos vision algorithm design system.

This module provides a singleton-based logging architecture with both file and 
console handlers. File logs use daily rotation with structured formatting.

SECURITY: Never log API keys or sensitive data. Add sanitization where needed.
"""

import logging
import logging.handlers
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from config.paths import LOGS_DIR


class LogLevel(Enum):
    """Log levels for the Argos system."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ArgosLogger:
    """
    Singleton logger manager for the Argos system.
    
    Provides file logging with daily rotation and optional console output.
    Uses singleton pattern to ensure only one logger instance per process.
    """
    
    _instance: Optional["ArgosLogger"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "ArgosLogger":
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the logger (only once due to singleton pattern)."""
        if ArgosLogger._initialized:
            return
            
        self._setup_logging()
        ArgosLogger._initialized = True
    
    def _setup_logging(self) -> None:
        """Setup the root logger with file and console handlers."""
        LOGS_DIR.mkdir(exist_ok=True)
        
        self._root_logger = logging.getLogger("argos")
        self._root_logger.setLevel(logging.DEBUG)
        
        if not self._root_logger.handlers:
            self._add_file_handler()
            self._add_console_handler()
    
    def _add_file_handler(self) -> None:
        """Add file handler with daily rotation."""
        log_file = LOGS_DIR / f"argos_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        
        self._root_logger.addHandler(file_handler)
        self._file_handler = file_handler
    
    def _add_console_handler(self) -> None:
        """Add console handler."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        console_formatter = logging.Formatter(
            "[%(levelname)s] [%(name)s] %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        
        self._root_logger.addHandler(console_handler)
        self._console_handler = console_handler
    
    def get(self, name: str) -> logging.Logger:
        """Get a named logger instance."""
        return logging.getLogger(f"argos.{name}")
    
    def set_level(self, level: LogLevel) -> None:
        """Set the logging level for all handlers."""
        self._root_logger.setLevel(level.value)
        
        for handler in self._root_logger.handlers:
            if isinstance(handler, logging.handlers.TimedRotatingFileHandler):
                handler.setLevel(logging.DEBUG)
            else:
                handler.setLevel(level.value)
    
    def disable_console(self) -> None:
        """Disable console logging (useful for test environments)."""
        if hasattr(self, "_console_handler") and self._console_handler in self._root_logger.handlers:
            self._root_logger.removeHandler(self._console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with proper file and console handlers.
    
    Args:
        name: The logger name (will be prefixed with 'argos.')
        
    Returns:
        A configured logger instance
    """
    logger_manager = ArgosLogger()
    return logger_manager.get(name)