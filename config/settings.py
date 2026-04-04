"""
Settings management for the Argos vision algorithm design system.

This module provides a robust settings system with validation, serialization,
and default value management following production best practices.
"""

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict

from .constants import (
    DEFAULT_SCORE_THRESHOLD,
    DEFAULT_MARGIN_WARNING,
    DEFAULT_W1,
    DEFAULT_W2,
    NG_MINIMUM_RECOMMENDED,
    NG_ABSOLUTE_MINIMUM,
    AI_TIMEOUT_SECONDS,
    AI_RETRY_COUNT
)


@dataclass
class Settings:
    """Application settings with validation and persistence."""
    
    score_threshold: float = DEFAULT_SCORE_THRESHOLD
    margin_warning: float = DEFAULT_MARGIN_WARNING
    w1: float = DEFAULT_W1
    w2: float = DEFAULT_W2
    ng_minimum_recommended: int = NG_MINIMUM_RECOMMENDED
    ng_absolute_minimum: int = NG_ABSOLUTE_MINIMUM
    ai_timeout: int = AI_TIMEOUT_SECONDS
    ai_retry: int = AI_RETRY_COUNT
    log_dir: str = "logs"
    output_dir: str = "output"

    def save(self, path: str) -> None:
        """
        Serialize settings to JSON file.
        
        Args:
            path: File path to save settings to
        
        Raises:
            ValueError: If settings validation fails
            OSError: If file cannot be written
        """
        self.validate()
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> 'Settings':
        """
        Deserialize settings from JSON file.
        
        Args:
            path: File path to load settings from
            
        Returns:
            Settings instance loaded from file
            
        Raises:
            FileNotFoundError: If settings file doesn't exist
            ValueError: If JSON is invalid or settings validation fails
        """
        with open(path, 'r', encoding='utf-8') as f:
            data: Dict[str, Any] = json.load(f)
        
        settings = cls(**data)
        settings.validate()
        return settings

    def validate(self) -> None:
        """
        Validate all settings are within acceptable ranges.
        
        Raises:
            ValueError: If any setting is invalid with descriptive message
        """
        if not (50.0 <= self.score_threshold <= 95.0):
            raise ValueError(
                f"score_threshold must be between 50.0 and 95.0, got {self.score_threshold}"
            )
        
        if not abs((self.w1 + self.w2) - 1.0) < 1e-6:
            raise ValueError(
                f"w1 + w2 must equal 1.0, got w1={self.w1}, w2={self.w2} (sum={self.w1 + self.w2})"
            )
        
        if self.ai_timeout <= 0:
            raise ValueError(
                f"ai_timeout must be positive, got {self.ai_timeout}"
            )
        
        if self.ai_retry < 0:
            raise ValueError(
                f"ai_retry must be non-negative, got {self.ai_retry}"
            )
        
        if self.margin_warning < 0:
            raise ValueError(
                f"margin_warning must be non-negative, got {self.margin_warning}"
            )
        
        if self.ng_absolute_minimum < 1:
            raise ValueError(
                f"ng_absolute_minimum must be at least 1, got {self.ng_absolute_minimum}"
            )
        
        if self.ng_minimum_recommended < self.ng_absolute_minimum:
            raise ValueError(
                f"ng_minimum_recommended ({self.ng_minimum_recommended}) must be >= "
                f"ng_absolute_minimum ({self.ng_absolute_minimum})"
            )

    @classmethod
    def reset(cls) -> 'Settings':
        """
        Create a new Settings instance with all default values.
        
        Returns:
            Settings instance with factory defaults
        """
        return cls()