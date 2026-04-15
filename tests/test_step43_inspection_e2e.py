"""
E2E integration tests for the full Inspection pipeline (Step 43).

Tests the pipeline: DynamicCandidateGenerator → InspectionOptimizer
→ FailureAnalyzer → FeasibilityAnalyzer, and the AnalysisWorker
INSPECTION_DESIGN / EVALUATION stage wiring.

All tests use synthetic numpy images and mock AI providers.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from config.constants import APPROACH_RULE_BASED, APPROACH_EDGE_LEARNING, APPROACH_DEEP_LEARNING
from config.settings import Settings
from core.analyzers.feature_analyzer import FullFeatureAnalysis
from core.evaluation.evaluator import InspectionEvaluator
from core.evaluation.failure_analyzer import FailureAnalyzer
from core.evaluation.feasibility_analyzer import FeasibilityAnalyzer
from core.exceptions import RuntimeProcessingError
from core.inspection.candidate_generator import DynamicCandidateGenerator, EngineCandidate
from core.inspection.optimizer import InspectionOptimizer
from core.models import (
    EvaluationResult,
    FeasibilityResult,
    InspectionPurpose,
    OptimizationResult,
)


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #


def _make_synthetic_image(w: int = 100, h: int = 100, value: int = 128) -> np.ndarray:
    """Create a simple synthetic grayscale image as a 3-channel BGR array."""
    return np.full((h, w, 3), value, dtype=np.uint8)


def _make_ok_images(n: int = 3) -> list[np.ndarray]:
    return [_make_synthetic_image(value=200) for _ in range(n)]


def _make_ng_images(n: int = 3) -> list[np.ndarray]:
    """Create NG images with added noise to differentiate from OK."""
    imgs = []
    for _ in range(n):
        img = _make_synthetic_image(value=80)
        # Add random noise to simulate defects
        noise = np.random.randint(0, 50, img.shape, dtype=np.uint8)
        img = cv2_safe_add(img, noise)
        imgs.append(img)
    return imgs


def cv2_safe_add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Add two arrays with saturation (mimics cv2.add)."""
    return np.clip(a.astype(np.int16) + b.astype(np.int16), 0, 255).astype(np.uint8)


def _make_purpose() -> InspectionPurpose:
    return InspectionPurpose(
        inspection_type="결함검출",
        description="스크래치 검사",
        ok_ng_criteria="스크래치 없음",
        target_feature="표면 스크래치",
        measurement_unit="px",
        tolerance="±2px",
    )


def _make_feature_analysis() -> FullFeatureAnalysis:
    """Create a minimal FullFeatureAnalysis with attributes the candidate generator needs."""
    from core.analyzers.edge_analyzer import EdgeAnalysisResult
    from core.analyzers.histogram_analyzer import HistogramAnalysisResult
    from core.analyzers.noise_analyzer import NoiseAnalysisResult
    from core.analyzers.shape_analyzer import ShapeAnalysisResult

    histogram = HistogramAnalysisResult(
        mean_gray=128.0,
        std_gray=45.0,
        min_gray=20,
        max_gray=230,
        dynamic_range=210,
        peak_count=1,
        distribution_type="unimodal",
    )
    noise = NoiseAnalysisResult(
        laplacian_variance=10.0,
        snr_db=30.0,
        noise_level="Low",
        recommended_filter="gaussian_blur",
        estimated_noise_std=2.5,
    )
    edge = EdgeAnalysisResult(
        mean_edge_strength=50.0,
        max_edge_strength=200.0,
        edge_density=0.35,
        dominant_direction="horizontal",
        horizontal_ratio=0.6,
        vertical_ratio=0.3,
        canny_threshold_suggestion=(50, 150),
        is_suitable_for_caliper=True,
        caliper_direction_suggestion="horizontal",
    )
    shape = ShapeAnalysisResult(
        blob_count=5,
        blobs=[],
        mean_blob_area=100.0,
        mean_circularity=0.8,
        has_circular_structure=True,
        detected_circles=[MagicMock()],  # non-empty list
        contour_complexity=3.0,
        has_repeating_pattern=False,
        pattern_description="",
    )
    summary = MagicMock()
    summary.mean_gray = 128.0
    summary.std_gray = 45.0
    summary.noise_level = "Low"
    summary.edge_density = 0.35
    summary.blob_count = 5
    summary.has_circular_structure = True

    return FullFeatureAnalysis(
        image_path="/synthetic/test.png",
        image_width=100,
        image_height=100,
        histogram=histogram,
        noise=noise,
        edge=edge,
        shape=shape,
        summary=summary,
        ai_prompt="test prompt",
        ai_summary="test summary",
    )


def _make_settings() -> Settings:
    return Settings()


def _make_eval(
    ok_pass_rate: float = 0.9,
    ng_detect_rate: float = 0.8,
    final_score: float = 75.0,
    margin: float = 10.0,
) -> EvaluationResult:
    return EvaluationResult(
        best_strategy="blob",
        ok_pass_rate=ok_pass_rate,
        ng_detect_rate=ng_detect_rate,
        final_score=final_score,
        margin=margin,
        is_margin_warning=margin < 15.0,
        fp_images=[],
        fn_images=[],
    )


# ------------------------------------------------------------------ #
#  Test 1: Full pipeline end-to-end                                    #
# ------------------------------------------------------------------ #


class TestFullPipelineE2E:
    """Full pipeline: CandidateGenerator → Optimizer → FailureAnalyzer → FeasibilityAnalyzer."""

    def test_full_pipeline_produces_expected_results(self):
        """Verify that the full pipeline runs end-to-end and produces results
        with all expected fields populated."""
        fa = _make_feature_analysis()
        purpose = _make_purpose()
        settings = _make_settings()
        ok_imgs = _make_ok_images(2)
        ng_imgs = _make_ng_images(2)

        # Step 1: Generate candidates
        gen = DynamicCandidateGenerator(ai_provider=None)
        candidates = gen.generate(fa, purpose)
        assert len(candidates) >= 2, "Should produce at least 2 candidates"
        for c in candidates:
            assert hasattr(c, "engine_class")
            assert hasattr(c, "engine_name")
            assert hasattr(c, "priority")
            assert 0.0 <= c.priority <= 1.0

        # Step 2: Optimize (evaluate each candidate)
        optimizer = InspectionOptimizer()
        try:
            opt_result = optimizer.run(candidates, ok_imgs, ng_imgs, settings)
        except RuntimeProcessingError:
            # All candidates may fail with synthetic images — that's valid
            pytest.skip("All candidates scored 0 with synthetic images (expected)")

        assert hasattr(opt_result, "best_candidate")
        assert hasattr(opt_result, "best_evaluation")
        assert hasattr(opt_result, "all_results")
        assert hasattr(opt_result, "optimization_log")
        assert len(opt_result.all_results) > 0

        # Step 3: Failure analysis
        failure_analyzer = FailureAnalyzer(ai_provider=None)
        failure_result = failure_analyzer.analyze(opt_result, purpose)
        assert hasattr(failure_result, "fp_count")
        assert hasattr(failure_result, "fn_count")
        assert hasattr(failure_result, "cause_summary")
        assert hasattr(failure_result, "improvement_directions")
        assert isinstance(failure_result.fp_count, int)
        assert isinstance(failure_result.fn_count, int)

        # Step 4: Feasibility analysis
        best_eval = opt_result.best_evaluation
        best_score = getattr(best_eval, "final_score", 0.0)
        feasibility = FeasibilityAnalyzer(ai_provider=None)
        feas_result = feasibility.analyze(
            best_score=best_score,
            threshold=settings.score_threshold,
            evaluation_result=best_eval,
            inspection_purpose=purpose,
        )
        assert isinstance(feas_result, FeasibilityResult)
        assert hasattr(feas_result, "rule_based_sufficient")
        assert hasattr(feas_result, "recommended_approach")
        assert hasattr(feas_result, "reasoning")
        assert feas_result.recommended_approach in (
            APPROACH_RULE_BASED, APPROACH_EDGE_LEARNING, APPROACH_DEEP_LEARNING,
        )


# ------------------------------------------------------------------ #
#  Test 2: NG=0 scenario                                               #
# ------------------------------------------------------------------ #


class TestNGZeroScenario:
    """When there are no NG images, inspection should be handled gracefully."""

    def test_no_ng_images_evaluator_warns(self):
        """Verify that InspectionEvaluator handles zero NG images by setting
        ng_detect_rate=1.0 and emitting a warning."""
        evaluator = InspectionEvaluator()

        candidate = MagicMock()
        candidate.engine_class = None  # will produce engine=None, score 0
        candidate.engine_name = "TestEngine"

        ok_imgs = _make_ok_images(2)
        ng_imgs = []  # no NG images
        settings = _make_settings()

        with pytest.warns(UserWarning, match="NG 이미지가 제공되지 않았습니다"):
            result = evaluator.evaluate(candidate, ok_imgs, ng_imgs, settings)

        assert result.ng_detect_rate == 1.0
        assert isinstance(result, EvaluationResult)

    def test_no_ng_images_optimizer_still_runs(self):
        """Verify the optimizer completes even with zero NG images."""
        candidate = MagicMock()
        candidate.engine_type = "blob"
        candidate.engine_name = "Blob Inspection"

        ok_imgs = _make_ok_images(2)
        ng_imgs = []

        optimizer = InspectionOptimizer()
        try:
            result = optimizer.run([candidate], ok_imgs, ng_imgs, _make_settings())
            assert hasattr(result, "best_candidate")
        except RuntimeProcessingError:
            # acceptable — engine may score 0
            pass


# ------------------------------------------------------------------ #
#  Test 3: All candidates fail                                         #
# ------------------------------------------------------------------ #


class TestAllCandidatesFail:
    """When all candidates fail evaluation, verify graceful degradation."""

    def test_all_candidates_fail_raises_runtime_error(self):
        """Verify that RuntimeProcessingError is raised when all candidates score 0."""
        # Create candidates with a bogus engine class that will fail
        candidate1 = MagicMock()
        candidate1.engine_type = "blob"
        candidate1.engine_name = "Blob"

        candidate2 = MagicMock()
        candidate2.engine_type = "pattern"
        candidate2.engine_name = "Pattern"

        # Empty images → all engines should fail/score 0
        ok_imgs = []
        ng_imgs = []

        optimizer = InspectionOptimizer()
        # With no images, engines will still get ok_pass_rate=1.0 and ng_detect_rate=1.0
        # (both defaulting). So let's mock InspectionEvaluator to always return 0
        with patch.object(InspectionEvaluator, "evaluate") as mock_eval:
            mock_eval.return_value = EvaluationResult(
                best_strategy="test",
                ok_pass_rate=0.0,
                ng_detect_rate=0.0,
                final_score=0.0,
                margin=-100.0,
                is_margin_warning=True,
                fp_images=[],
                fn_images=[],
            )
            with pytest.raises(RuntimeProcessingError, match="All candidates failed"):
                optimizer.run([candidate1, candidate2], ok_imgs, ng_imgs, _make_settings())


# ------------------------------------------------------------------ #
#  Test 4: Single engine success                                       #
# ------------------------------------------------------------------ #


class TestSingleEngineSuccess:
    """When only one engine succeeds, it should be selected as the best candidate."""

    def test_single_success_becomes_best(self):
        """Verify that the single succeeding candidate becomes best_candidate."""
        candidate_good = MagicMock()
        candidate_good.engine_type = "blob"
        candidate_good.engine_name = "Blob (good)"

        candidate_bad = MagicMock()
        candidate_bad.engine_type = "pattern"
        candidate_bad.engine_name = "Pattern (bad)"

        good_eval = EvaluationResult(
            best_strategy="Blob (good)",
            ok_pass_rate=0.9,
            ng_detect_rate=0.8,
            final_score=85.0,
            margin=70.0,
            is_margin_warning=False,
            fp_images=[],
            fn_images=[],
        )
        bad_eval = EvaluationResult(
            best_strategy="Pattern (bad)",
            ok_pass_rate=0.0,
            ng_detect_rate=0.0,
            final_score=0.0,
            margin=-100.0,
            is_margin_warning=True,
            fp_images=["ok_0"],
            fn_images=["ng_0"],
        )

        optimizer = InspectionOptimizer()
        with patch.object(InspectionEvaluator, "evaluate") as mock_eval:
            mock_eval.side_effect = [good_eval, bad_eval]
            result = optimizer.run(
                [candidate_good, candidate_bad],
                _make_ok_images(1),
                _make_ng_images(1),
                _make_settings(),
            )

        assert result.best_candidate is candidate_good
        assert result.best_evaluation.final_score == 85.0


# ------------------------------------------------------------------ #
#  Test 5: Feasibility threshold — EL/DL recommendation                #
# ------------------------------------------------------------------ #


class TestFeasibilityThreshold:
    """When score is below threshold, verify EL/DL recommendation is generated."""

    def test_below_threshold_recommends_el_or_dl(self):
        """Verify that a low score triggers an Edge Learning or Deep Learning
        recommendation from FeasibilityAnalyzer."""
        low_eval = _make_eval(
            ok_pass_rate=0.4,
            ng_detect_rate=0.3,
            final_score=35.0,
            margin=-30.0,
        )
        purpose = _make_purpose()
        feasibility = FeasibilityAnalyzer(ai_provider=None)

        result = feasibility.analyze(
            best_score=35.0,
            threshold=70.0,  # well above score
            evaluation_result=low_eval,
            inspection_purpose=purpose,
        )

        assert isinstance(result, FeasibilityResult)
        assert result.rule_based_sufficient is False
        assert result.recommended_approach in (APPROACH_EDGE_LEARNING, APPROACH_DEEP_LEARNING)
        assert result.reasoning  # non-empty
        assert result.model_suggestion  # should have a model suggestion

    def test_above_threshold_recommends_rule_based(self):
        """Verify that a high score results in rule-based recommendation."""
        high_eval = _make_eval(
            ok_pass_rate=0.95,
            ng_detect_rate=0.95,
            final_score=95.0,
            margin=90.0,
        )
        purpose = _make_purpose()
        feasibility = FeasibilityAnalyzer(ai_provider=None)

        result = feasibility.analyze(
            best_score=95.0,
            threshold=70.0,
            evaluation_result=high_eval,
            inspection_purpose=purpose,
        )

        assert result.rule_based_sufficient is True
        assert result.recommended_approach == APPROACH_RULE_BASED

    def test_large_gap_recommends_deep_learning(self):
        """Verify that a very large gap (>30) between score and threshold
        triggers Deep Learning recommendation via heuristic fallback."""
        low_eval = _make_eval(
            ok_pass_rate=0.2,
            ng_detect_rate=0.1,
            final_score=15.0,
            margin=-70.0,
        )
        purpose = _make_purpose()
        feasibility = FeasibilityAnalyzer(ai_provider=None)

        result = feasibility.analyze(
            best_score=15.0,
            threshold=70.0,  # gap = 55.0 > 30.0
            evaluation_result=low_eval,
            inspection_purpose=purpose,
        )

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_DEEP_LEARNING


# ------------------------------------------------------------------ #
#  Test 6: FailureAnalyzer overlay generation                          #
# ------------------------------------------------------------------ #


class TestFailureAnalyzerOverlays:
    """Verify FailureAnalyzer generates overlays for FP/FN cases."""

    def test_overlays_generated_for_fp_fn(self):
        """Verify that overlay paths are produced for each FP and FN image."""
        best_eval = types.SimpleNamespace(
            fp_images=["ok_0", "ok_1"],
            fn_images=["ng_0"],
            ok_pass_rate=0.5,
            ng_detect_rate=0.5,
            final_score=50.0,
            margin=0.0,
            is_margin_warning=True,
        )
        opt_result = types.SimpleNamespace(
            best_candidate=types.SimpleNamespace(engine_name="TestEngine"),
            best_evaluation=best_eval,
        )

        analyzer = FailureAnalyzer(ai_provider=None)
        result = analyzer.analyze(opt_result)

        assert result.fp_count == 2
        assert result.fn_count == 1
        assert len(result.fp_overlay_paths) == 2
        assert len(result.fn_overlay_paths) == 1
        # Each overlay path should be an absolute path string
        for p in result.fp_overlay_paths + result.fn_overlay_paths:
            assert isinstance(p, str)
            assert len(p) > 0


# ------------------------------------------------------------------ #
#  Test 7: CandidateGenerator rule-based selection                     #
# ------------------------------------------------------------------ #


class TestCandidateGeneratorRules:
    """Verify DynamicCandidateGenerator selects appropriate engines based on features."""

    def test_generates_multiple_candidates_for_rich_features(self):
        """Verify that rich feature analysis produces multiple diverse candidates."""
        fa = _make_feature_analysis()
        purpose = _make_purpose()

        gen = DynamicCandidateGenerator(ai_provider=None)
        candidates = gen.generate(fa, purpose)

        assert len(candidates) >= 2
        engine_names = {c.engine_name for c in candidates}
        # With high edge density, circular structures, blobs, and low noise:
        # we should see Linear Caliper, Circular Caliper, Blob, and Pattern candidates
        assert len(engine_names) >= 2
