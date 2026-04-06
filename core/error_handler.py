"""
Error handling utilities for the Argos vision algorithm design system.

This module provides decorators and utilities for handling exceptions in a 
consistent manner throughout the application, including logging and graceful 
degradation mechanisms.
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar

from core.exceptions import InputValidationError, RuntimeProcessingError
from core.logger import get_logger


F = TypeVar('F', bound=Callable[..., Any])


def handle_input_error(func: F) -> F:
    """
    Decorator that catches InputValidationError, logs it, and re-raises.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that logs InputValidationError before re-raising
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        try:
            return func(*args, **kwargs)
        except InputValidationError as e:
            logger.error(f"Input validation failed in {func.__name__}: {e}")
            raise
    
    return wrapper  # type: ignore


def handle_runtime_error(func: F) -> F:
    """
    Decorator that catches RuntimeProcessingError, logs it, and re-raises.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that logs RuntimeProcessingError before re-raising
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        try:
            return func(*args, **kwargs)
        except RuntimeProcessingError as e:
            logger.error(f"Runtime processing failed in {func.__name__}: {e}")
            raise
    
    return wrapper  # type: ignore


def safe_execute(
    func: Callable[..., Any], 
    *args: Any, 
    fallback: Any = None, 
    logger: Optional[logging.Logger] = None, 
    **kwargs: Any
) -> Any:
    """
    Execute a function safely, returning fallback value on any exception.
    
    This function never raises exceptions - it always returns a value,
    making it suitable for graceful degradation scenarios.
    
    Args:
        func: Function to execute
        *args: Positional arguments to pass to func
        fallback: Value to return if func raises an exception
        logger: Optional logger instance (will create one if not provided)
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result of func(*args, **kwargs) on success, fallback on any exception
    """
    if logger is None:
        logger = get_logger(f"safe_execute.{func.__name__}")
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Function {func.__name__} failed: {e}")
        return fallback