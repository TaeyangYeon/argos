"""
Data models for the Argos vision algorithm design system.

This module contains all dataclasses that represent the core data structures
used throughout the system for configuration, results, and analysis.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class ROIConfig:
    """Configuration for Region of Interest."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class AlignResult:
    """Result from alignment algorithm execution."""
    success: bool
    strategy_name: str
    score: float
    transform_matrix: Optional[np.ndarray] = field(default=None)
    failure_reason: Optional[str] = field(default=None)


@dataclass
class InspectionResult:
    """Result from inspection algorithm execution."""
    success: bool
    strategy_name: str
    score: float
    is_ok: bool
    failure_reason: Optional[str] = field(default=None)
    overlay_image: Optional[np.ndarray] = field(default=None)


@dataclass
class EvaluationResult:
    """Result from evaluation of multiple inspection candidates."""
    best_strategy: str
    ok_pass_rate: float
    ng_detect_rate: float
    final_score: float
    margin: float
    is_margin_warning: bool
    fp_images: list[str] = field(default_factory=list)
    fn_images: list[str] = field(default_factory=list)


@dataclass
class FeatureAnalysisSummary:
    """Summary of image feature analysis."""
    mean_gray: float
    std_gray: float
    noise_level: str  # "Low" | "Medium" | "High"
    edge_density: float
    blob_count: int
    has_circular_structure: bool
    ai_summary: Optional[str] = field(default=None)


@dataclass
class FeasibilityResult:
    """Result of feasibility analysis for algorithm approach."""
    rule_based_sufficient: bool
    recommended_approach: str  # "Rule-based" | "Edge Learning" | "Deep Learning"
    reasoning: str
    model_suggestion: Optional[str] = field(default=None)