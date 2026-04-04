"""
Abstract interfaces for the Argos vision algorithm design system.

This module defines the core interfaces that implement the SOLID principle of 
Dependency Inversion - all concrete implementations depend on these abstractions.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .models import (
        AlignResult,
        EvaluationResult, 
        FeatureAnalysisSummary,
        InspectionResult,
        ROIConfig
    )


class IAlignEngine(ABC):
    """Abstract interface for alignment algorithms."""
    
    @abstractmethod
    def run(self, image: np.ndarray, reference: np.ndarray) -> "AlignResult":
        """
        Execute alignment algorithm on the input image using reference.
        
        Args:
            image: Input image to align
            reference: Reference image for alignment
            
        Returns:
            AlignResult containing success status and transformation data
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of the alignment strategy.
        
        Returns:
            Human-readable strategy name (e.g., "Pattern Matching", "Caliper")
        """
        pass


class IInspectionEngine(ABC):
    """Abstract interface for inspection algorithms."""
    
    @abstractmethod
    def run(self, image: np.ndarray, roi: "ROIConfig") -> "InspectionResult":
        """
        Execute inspection algorithm on the image within specified ROI.
        
        Args:
            image: Input image to inspect
            roi: Region of interest configuration
            
        Returns:
            InspectionResult containing pass/fail status and score
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of the inspection strategy.
        
        Returns:
            Human-readable strategy name (e.g., "Blob Detection", "Caliper")
        """
        pass


class IEvaluationEngine(ABC):
    """Abstract interface for evaluation of inspection results."""
    
    @abstractmethod
    def evaluate(self, results: list["InspectionResult"]) -> "EvaluationResult":
        """
        Evaluate multiple inspection results to determine best algorithm.
        
        Args:
            results: List of inspection results from different algorithms
            
        Returns:
            EvaluationResult with performance metrics and best strategy
        """
        pass
    
    @abstractmethod
    def get_score(self) -> float:
        """
        Get the current evaluation score.
        
        Returns:
            Current score value between 0.0 and 100.0
        """
        pass


class IFeatureAnalyzer(ABC):
    """Abstract interface for image feature analysis."""
    
    @abstractmethod
    def analyze(self, image: np.ndarray) -> "FeatureAnalysisSummary":
        """
        Analyze image features to determine optimal algorithm candidates.
        
        Args:
            image: Input image to analyze
            
        Returns:
            FeatureAnalysisSummary with extracted features and characteristics
        """
        pass
    
    @abstractmethod
    def get_summary(self) -> str:
        """
        Get human-readable summary of the analysis.
        
        Returns:
            Text summary suitable for AI provider input
        """
        pass