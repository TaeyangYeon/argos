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
    """Abstract interface for evaluation of inspection engine candidates."""

    @abstractmethod
    def evaluate(
        self,
        candidate: object,
        ok_images: list,
        ng_images: list,
        settings: object,
    ) -> "EvaluationResult":
        """
        Evaluate a single engine candidate against OK and NG image sets.

        Args:
            candidate: EngineCandidate with engine_class and engine_name fields.
            ok_images: List of numpy arrays representing OK (pass) images.
            ng_images: List of numpy arrays representing NG (fail) images.
            settings:  Settings instance carrying w1, w2, score_threshold,
                       and margin_warning.

        Returns:
            EvaluationResult with performance metrics and best strategy.
        """
        pass

    @abstractmethod
    def get_score(self) -> float:
        """
        Return the final_score from the most recent evaluate() call.

        Returns:
            Score in [0.0, 100.0]; 0.0 before the first evaluation.
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