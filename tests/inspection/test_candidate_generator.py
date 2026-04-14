"""
Tests for DynamicCandidateGenerator (Step 38).

Covers rule-based selection, AI augmentation, fallback, deduplication,
priority ordering, and field contract for EngineCandidate.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from core.analyzers.edge_analyzer import EdgeAnalysisResult
from core.analyzers.histogram_analyzer import HistogramAnalysisResult
from core.analyzers.noise_analyzer import NoiseAnalysisResult
from core.analyzers.shape_analyzer import BlobInfo, CircleInfo, ShapeAnalysisResult
from core.analyzers.feature_analyzer import FullFeatureAnalysis
from core.inspection.blob_inspector import BlobInspectionEngine
from core.inspection.circular_caliper_inspector import CircularCaliperInspectionEngine
from core.inspection.candidate_generator import DynamicCandidateGenerator, EngineCandidate
from core.inspection.linear_caliper_inspector import LinearCaliperInspectionEngine
from core.inspection.pattern_inspector import PatternInspectionEngine
from core.models import FeatureAnalysisSummary, InspectionPurpose


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_edge(
    edge_density: float = 0.05,
    is_suitable_for_caliper: bool = False,
    mean_edge_strength: float = 5.0,
) -> EdgeAnalysisResult:
    return EdgeAnalysisResult(
        mean_edge_strength=mean_edge_strength,
        max_edge_strength=mean_edge_strength * 2,
        edge_density=edge_density,
        dominant_direction="mixed",
        horizontal_ratio=0.5,
        vertical_ratio=0.5,
        canny_threshold_suggestion=(50, 100),
        is_suitable_for_caliper=is_suitable_for_caliper,
        caliper_direction_suggestion="both",
    )


def _make_noise(noise_level: str = "Low") -> NoiseAnalysisResult:
    return NoiseAnalysisResult(
        laplacian_variance=50.0,
        snr_db=30.0,
        noise_level=noise_level,
        recommended_filter="gaussian_blur",
        estimated_noise_std=2.0,
    )


def _make_histogram(std_gray: float = 50.0, mean_gray: float = 128.0) -> HistogramAnalysisResult:
    return HistogramAnalysisResult(
        mean_gray=mean_gray,
        std_gray=std_gray,
        min_gray=0,
        max_gray=255,
        dynamic_range=255,
        peak_count=2,
        distribution_type="bimodal",
    )


def _make_shape(
    blob_count: int = 0,
    blobs: list | None = None,
    detected_circles: list | None = None,
    has_circular_structure: bool = False,
) -> ShapeAnalysisResult:
    return ShapeAnalysisResult(
        blob_count=blob_count,
        blobs=blobs or [],
        mean_blob_area=0.0,
        mean_circularity=0.0,
        has_circular_structure=has_circular_structure,
        detected_circles=detected_circles or [],
        contour_complexity=0.0,
        has_repeating_pattern=False,
        pattern_description="반복 패턴 없음",
    )


def _make_full_analysis(
    edge: EdgeAnalysisResult | None = None,
    noise: NoiseAnalysisResult | None = None,
    histogram: HistogramAnalysisResult | None = None,
    shape: ShapeAnalysisResult | None = None,
) -> FullFeatureAnalysis:
    edge = edge or _make_edge()
    noise = noise or _make_noise()
    histogram = histogram or _make_histogram()
    shape = shape or _make_shape()
    summary = FeatureAnalysisSummary(
        mean_gray=histogram.mean_gray,
        std_gray=histogram.std_gray,
        noise_level=noise.noise_level,
        edge_density=edge.edge_density,
        blob_count=shape.blob_count,
        has_circular_structure=shape.has_circular_structure,
    )
    return FullFeatureAnalysis(
        image_path="test.png",
        image_width=640,
        image_height=480,
        histogram=histogram,
        noise=noise,
        edge=edge,
        shape=shape,
        summary=summary,
        ai_prompt="",
        ai_summary="",
    )


def _make_purpose(description: str = "치수 검사") -> InspectionPurpose:
    return InspectionPurpose(
        inspection_type="치수측정",
        description=description,
        ok_ng_criteria="허용 공차 ±0.1mm",
        target_feature="홀 지름",
        measurement_unit="mm",
        tolerance="0.1",
    )


def _blob_info() -> BlobInfo:
    return BlobInfo(
        area=500.0, perimeter=100.0, circularity=0.6,
        aspect_ratio=1.0, centroid_x=100.0, centroid_y=100.0, mean_gray=128.0,
    )


def _circle_info() -> CircleInfo:
    return CircleInfo(center_x=100.0, center_y=100.0, radius=30.0, confidence=1.0)


# ---------------------------------------------------------------------------
# Test 1 — rule_based_high_edge_density_adds_linear_caliper
# ---------------------------------------------------------------------------

def test_rule_based_high_edge_density_adds_linear_caliper():
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.4, is_suitable_for_caliper=True)
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    engine_classes = [c.engine_class for c in candidates]
    assert LinearCaliperInspectionEngine in engine_classes


# ---------------------------------------------------------------------------
# Test 2 — rule_based_circular_blobs_adds_circular_caliper
# ---------------------------------------------------------------------------

def test_rule_based_circular_blobs_adds_circular_caliper():
    fa = _make_full_analysis(
        shape=_make_shape(
            detected_circles=[_circle_info()],
            has_circular_structure=True,
        )
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    engine_classes = [c.engine_class for c in candidates]
    assert CircularCaliperInspectionEngine in engine_classes


# ---------------------------------------------------------------------------
# Test 3 — rule_based_high_blob_count_adds_blob_inspector
# ---------------------------------------------------------------------------

def test_rule_based_high_blob_count_adds_blob_inspector():
    blobs = [_blob_info(), _blob_info(), _blob_info()]
    fa = _make_full_analysis(
        shape=_make_shape(blob_count=3, blobs=blobs)
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    engine_classes = [c.engine_class for c in candidates]
    assert BlobInspectionEngine in engine_classes


# ---------------------------------------------------------------------------
# Test 4 — rule_based_low_noise_high_contrast_adds_pattern
# ---------------------------------------------------------------------------

def test_rule_based_low_noise_high_contrast_adds_pattern():
    fa = _make_full_analysis(
        noise=_make_noise(noise_level="Low"),
        histogram=_make_histogram(std_gray=60.0),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    engine_classes = [c.engine_class for c in candidates]
    assert PatternInspectionEngine in engine_classes


# ---------------------------------------------------------------------------
# Test 5 — minimum_two_candidates_guaranteed
# ---------------------------------------------------------------------------

def test_minimum_two_candidates_guaranteed():
    # Deliberately empty analysis — no rule should fire
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.0, is_suitable_for_caliper=False),
        noise=_make_noise(noise_level="High"),
        histogram=_make_histogram(std_gray=5.0),
        shape=_make_shape(blob_count=0),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    assert len(candidates) >= 2


# ---------------------------------------------------------------------------
# Test 6 — candidates_sorted_by_priority_descending
# ---------------------------------------------------------------------------

def test_candidates_sorted_by_priority_descending():
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.5, is_suitable_for_caliper=True),
        noise=_make_noise(noise_level="Low"),
        histogram=_make_histogram(std_gray=80.0),
        shape=_make_shape(
            blob_count=5,
            blobs=[_blob_info()] * 5,
            detected_circles=[_circle_info()],
        ),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    priorities = [c.priority for c in candidates]
    assert priorities == sorted(priorities, reverse=True)


# ---------------------------------------------------------------------------
# Test 7 — candidate_has_required_fields
# ---------------------------------------------------------------------------

def test_candidate_has_required_fields():
    fa = _make_full_analysis()
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    for candidate in candidates:
        assert hasattr(candidate, "engine_class")
        assert hasattr(candidate, "engine_name")
        assert hasattr(candidate, "priority")
        assert hasattr(candidate, "rationale")
        assert hasattr(candidate, "source")
        assert isinstance(candidate.engine_class, type)
        assert isinstance(candidate.engine_name, str) and candidate.engine_name
        assert isinstance(candidate.priority, float)
        assert isinstance(candidate.rationale, str) and candidate.rationale
        assert candidate.source in ("rule_based", "ai_suggested")


# ---------------------------------------------------------------------------
# Test 8 — ai_failure_falls_back_to_rule_based
# ---------------------------------------------------------------------------

def test_ai_failure_falls_back_to_rule_based():
    mock_provider = MagicMock()
    mock_provider.analyze.side_effect = RuntimeError("network error")

    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.5, is_suitable_for_caliper=True)
    )
    gen = DynamicCandidateGenerator(ai_provider=mock_provider)
    candidates = gen.generate(fa, _make_purpose())

    # Should still return rule-based results despite AI failure
    assert len(candidates) >= 2
    assert any(c.source == "rule_based" for c in candidates)


# ---------------------------------------------------------------------------
# Test 9 — ai_suggested_candidate_has_source_ai_suggested
# ---------------------------------------------------------------------------

def test_ai_suggested_candidate_has_source_ai_suggested():
    mock_provider = MagicMock()
    mock_provider.analyze.return_value = json.dumps({
        "candidates": [
            {"engine": "BlobInspectionEngine", "rationale": "AI thinks blobs matter"}
        ]
    })

    # Use edge analysis that does NOT trigger BlobInspectionEngine via rules
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.0, is_suitable_for_caliper=False),
        noise=_make_noise(noise_level="High"),
        histogram=_make_histogram(std_gray=5.0),
        shape=_make_shape(blob_count=0),
    )
    gen = DynamicCandidateGenerator(ai_provider=mock_provider)
    candidates = gen.generate(fa, _make_purpose())

    ai_candidates = [c for c in candidates if c.source == "ai_suggested"]
    assert len(ai_candidates) >= 1
    assert ai_candidates[0].engine_class is BlobInspectionEngine


# ---------------------------------------------------------------------------
# Test 10 — no_duplicate_engine_classes_in_result
# ---------------------------------------------------------------------------

def test_no_duplicate_engine_classes_in_result():
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.5, is_suitable_for_caliper=True),
        noise=_make_noise(noise_level="Low"),
        histogram=_make_histogram(std_gray=80.0),
        shape=_make_shape(
            blob_count=5,
            blobs=[_blob_info()] * 5,
            detected_circles=[_circle_info()],
        ),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    engine_classes = [c.engine_class for c in candidates]
    assert len(engine_classes) == len(set(engine_classes))


# ---------------------------------------------------------------------------
# Test 11 — inspection_purpose_text_included_in_ai_prompt
# ---------------------------------------------------------------------------

def test_inspection_purpose_text_included_in_ai_prompt():
    mock_provider = MagicMock()
    mock_provider.analyze.return_value = json.dumps({"candidates": []})

    fa = _make_full_analysis()
    gen = DynamicCandidateGenerator(ai_provider=mock_provider)
    purpose = _make_purpose(description="스크래치 결함 검출")

    gen.generate(fa, purpose)

    mock_provider.analyze.assert_called_once()
    prompt_used = mock_provider.analyze.call_args[0][0]
    assert "스크래치 결함 검출" in prompt_used


# ---------------------------------------------------------------------------
# Test 12 — empty_feature_analysis_returns_fallback_candidates
# ---------------------------------------------------------------------------

def test_empty_feature_analysis_returns_fallback_candidates():
    # All metrics at zero/minimum — no rule fires
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.0, is_suitable_for_caliper=False),
        noise=_make_noise(noise_level="High"),
        histogram=_make_histogram(std_gray=0.0),
        shape=_make_shape(blob_count=0),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    assert len(candidates) >= 2
    # At least one should be the PatternInspectionEngine fallback
    assert any(c.engine_class is PatternInspectionEngine for c in candidates)


# ---------------------------------------------------------------------------
# Test 13 — priority_range_0_to_1
# ---------------------------------------------------------------------------

def test_priority_range_0_to_1():
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.9, is_suitable_for_caliper=True),
        noise=_make_noise(noise_level="Low"),
        histogram=_make_histogram(std_gray=100.0),
        shape=_make_shape(
            blob_count=10,
            blobs=[_blob_info()] * 10,
            detected_circles=[_circle_info(), _circle_info()],
        ),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    for candidate in candidates:
        assert 0.0 <= candidate.priority <= 1.0


# ---------------------------------------------------------------------------
# Test 14 — rule_based_source_label_correct
# ---------------------------------------------------------------------------

def test_rule_based_source_label_correct():
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.5, is_suitable_for_caliper=True)
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    linear_caliper = next(
        (c for c in candidates if c.engine_class is LinearCaliperInspectionEngine), None
    )
    assert linear_caliper is not None
    assert linear_caliper.source == "rule_based"


# ---------------------------------------------------------------------------
# Test 15 — all_returned_engine_classes_implement_inspection_interface
# ---------------------------------------------------------------------------

def test_all_returned_engine_classes_implement_inspection_interface():
    """All engine_class entries must have run() and get_strategy_name() methods."""
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.5, is_suitable_for_caliper=True),
        noise=_make_noise(noise_level="Low"),
        histogram=_make_histogram(std_gray=80.0),
        shape=_make_shape(
            blob_count=3,
            blobs=[_blob_info()] * 3,
            detected_circles=[_circle_info()],
        ),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    for candidate in candidates:
        cls = candidate.engine_class
        assert callable(getattr(cls, "run", None)), (
            f"{cls.__name__} must have a run() method"
        )
        assert callable(getattr(cls, "get_strategy_name", None)), (
            f"{cls.__name__} must have a get_strategy_name() method"
        )


# ---------------------------------------------------------------------------
# Test 16 — low_edge_density_does_not_add_linear_caliper
# ---------------------------------------------------------------------------

def test_low_edge_density_does_not_add_linear_caliper():
    fa = _make_full_analysis(
        edge=_make_edge(edge_density=0.1, is_suitable_for_caliper=True)
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    engine_classes = [c.engine_class for c in candidates]
    assert LinearCaliperInspectionEngine not in engine_classes


# ---------------------------------------------------------------------------
# Test 17 — high_noise_does_not_add_pattern_inspector
# ---------------------------------------------------------------------------

def test_high_noise_does_not_add_pattern_inspector_via_rule():
    fa = _make_full_analysis(
        noise=_make_noise(noise_level="High"),
        histogram=_make_histogram(std_gray=80.0),
        edge=_make_edge(edge_density=0.0, is_suitable_for_caliper=False),
        shape=_make_shape(blob_count=0),
    )
    gen = DynamicCandidateGenerator()
    candidates = gen.generate(fa, _make_purpose())
    # PatternInspectionEngine may appear only as fallback (priority 0.3), not rule-based
    pattern_rule = [
        c for c in candidates
        if c.engine_class is PatternInspectionEngine and c.source == "rule_based"
        and "Low noise" in c.rationale
    ]
    assert len(pattern_rule) == 0
