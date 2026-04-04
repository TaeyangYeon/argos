"""
Custom exceptions for the Argos vision algorithm design system.

This module defines the exception hierarchy implementing the 3-layer error 
handling strategy as defined in the project plan.
"""


class InputValidationError(Exception):
    """
    Layer 1: Input validation errors.
    
    Raised when input data fails validation (unsupported formats, 
    invalid ROI coordinates, insufficient sample data, etc.)
    """
    pass


class RuntimeProcessingError(Exception):
    """
    Layer 2: Runtime processing errors.
    
    Raised during algorithm execution when processing cannot continue
    (algorithm execution failures, image processing errors, etc.)
    """
    pass


class OutputValidationError(Exception):
    """
    Layer 3: Output validation errors.
    
    Raised when generated results don't meet quality criteria
    (algorithm scores below threshold, validation failures, etc.)
    """
    pass


class AIProviderError(Exception):
    """
    AI provider communication errors.
    
    Raised when AI API calls fail due to network issues, authentication
    failures, rate limits, or invalid responses.
    """
    pass