"""
Data models for the Argos vision algorithm design system.

This module contains all dataclasses that represent the core data structures
used throughout the system for configuration, results, and analysis.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

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


@dataclass
class InspectionPurpose:
    """Configuration for inspection purpose and criteria."""
    inspection_type: str = ""  # 검사 유형: one of "치수측정" / "결함검출" / "형상검사" / "위치정렬" / "기타"
    description: str = ""      # 검사 상세 설명 (free text)
    ok_ng_criteria: str = ""   # OK/NG 판정 기준
    target_feature: str = ""   # 검사 대상 특징 (e.g. 홀 지름, 폭, 스크래치)
    measurement_unit: str = "" # 측정 단위 (mm, px, %)
    tolerance: str = ""        # 허용 공차
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())