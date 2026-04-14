"""
TDD tests for InspectionOptimizer (Argos Step 40).

Tests are written BEFORE the implementation to drive the design.
All 20 required test cases are covered.
"""

import numpy as np
import pytest
from unittest.mock import patch

from core.inspection.candidate_generator import EngineCandidate
from core.inspection.blob_inspector import BlobInspectionEngine
from core.inspection.circular_caliper_inspector import CircularCaliperInspectionEngine
from core.inspection.linear_caliper_inspector import LinearCaliperInspectionEngine
from core.inspection.pattern_inspector import PatternInspectionEngine
from core.models import EvaluationResult, OptimizationResult
from core.inspection.optimizer import InspectionOptimizer
from core.exceptions import RuntimeProcessingError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candidate(engine_class, engine_name: str = "test_engine") -> EngineCandidate:
    return EngineCandidate(
        engine_class=engine_class,
        engine_name=engine_name,
        priority=0.5,
        rationale="test rationale",
        source="rule_based",
    )


def _make_eval_result(
    score: float = 80.0,
    ok_pass_rate: float = 0.9,
    ng_detect_rate: float = 0.7,
    is_margin_warning: bool = False,
) -> EvaluationResult:
    return EvaluationResult(
        best_strategy="test_strategy",
        ok_pass_rate=ok_pass_rate,
        ng_detect_rate=ng_detect_rate,
        final_score=score,
        margin=60.0,
        is_margin_warning=is_margin_warning,
        fp_images=[],
        fn_images=[],
    )


class _DummySettings:
    w1 = 0.5
    w2 = 0.5
    margin_warning = 15.0


SETTINGS = _DummySettings()
OK_IMAGES = [np.zeros((100, 100), dtype=np.uint8)]
NG_IMAGES = [np.ones((100, 100), dtype=np.uint8) * 255]

_PATCH = "core.inspection.optimizer.InspectionEvaluator"


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestInspectionOptimizer:

    def setup_method(self):
        self.optimizer = InspectionOptimizer()

    # 1 ── return type
    def test_returns_optimization_result_type(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(75.0)
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)
        assert isinstance(result, OptimizationResult)

    # 2 ── best candidate is the one with highest score
    def test_selects_highest_score_candidate(self):
        c1 = _make_candidate(BlobInspectionEngine, "Blob")
        c2 = _make_candidate(CircularCaliperInspectionEngine, "Circular")
        c3 = _make_candidate(LinearCaliperInspectionEngine, "Linear")
        score_map = {"Blob": 60.0, "Circular": 90.0, "Linear": 75.0}

        def _se(candidate, *_args):
            return _make_eval_result(score=score_map[candidate.engine_name])

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.side_effect = _se
            result = self.optimizer.run([c1, c2, c3], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert result.best_candidate is c2
        assert result.best_evaluation.final_score == pytest.approx(90.0)

    # 3 ── all_results sorted descending by score
    def test_results_sorted_descending(self):
        c1 = _make_candidate(BlobInspectionEngine, "Blob")
        c2 = _make_candidate(CircularCaliperInspectionEngine, "Circular")
        c3 = _make_candidate(LinearCaliperInspectionEngine, "Linear")
        score_map = {"Blob": 55.0, "Circular": 88.0, "Linear": 72.0}

        def _se(candidate, *_args):
            return _make_eval_result(score=score_map[candidate.engine_name])

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.side_effect = _se
            result = self.optimizer.run([c1, c2, c3], OK_IMAGES, NG_IMAGES, SETTINGS)

        out_scores = [r[1].final_score for r in result.all_results]
        assert out_scores == sorted(out_scores, reverse=True)

    # 4 ── single candidate still returns OptimizationResult
    def test_single_candidate_selected(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(65.0)
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert isinstance(result, OptimizationResult)
        assert result.best_candidate is c
        assert len(result.all_results) == 1

    # 5 ── exception in one candidate → score=0.0, loop continues
    def test_failed_candidate_score_zero(self):
        c1 = _make_candidate(BlobInspectionEngine, "Blob")
        c2 = _make_candidate(PatternInspectionEngine, "Pattern")

        def _se(candidate, *_args):
            if candidate.engine_name == "Blob":
                raise RuntimeError("simulated crash")
            return _make_eval_result(score=80.0)

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.side_effect = _se
            result = self.optimizer.run([c1, c2], OK_IMAGES, NG_IMAGES, SETTINGS)

        failed = [r for r in result.all_results if r[0] is c1]
        assert len(failed) == 1
        assert failed[0][1].final_score == pytest.approx(0.0)
        assert result.best_candidate is c2

    # 6 ── all candidates fail → RuntimeProcessingError
    def test_all_failed_raises_error(self):
        c1 = _make_candidate(BlobInspectionEngine, "Blob")
        c2 = _make_candidate(PatternInspectionEngine, "Pattern")

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.side_effect = RuntimeError("crash")
            with pytest.raises(RuntimeProcessingError):
                self.optimizer.run([c1, c2], OK_IMAGES, NG_IMAGES, SETTINGS)

    # 7 ── log mentions every processed candidate by name
    def test_optimization_log_contains_all_candidates(self):
        c1 = _make_candidate(BlobInspectionEngine, "Blob Engine")
        c2 = _make_candidate(PatternInspectionEngine, "Pattern Engine")

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            result = self.optimizer.run([c1, c2], OK_IMAGES, NG_IMAGES, SETTINGS)

        combined = " ".join(result.optimization_log)
        assert "Blob Engine" in combined
        assert "Pattern Engine" in combined

    # 8 ── ok_pass_rate from evaluator propagates to best_evaluation
    def test_ok_pass_rate_propagated(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(80.0, ok_pass_rate=0.95)
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert result.best_evaluation.ok_pass_rate == pytest.approx(0.95)

    # 9 ── ng_detect_rate from evaluator propagates to best_evaluation
    def test_ng_detect_rate_propagated(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(80.0, ng_detect_rate=0.88)
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert result.best_evaluation.ng_detect_rate == pytest.approx(0.88)

    # 10 ── BlobInspectionEngine dispatched via registry
    def test_engine_registry_dispatch_blob(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        MockEval.return_value.evaluate.assert_called_once()
        passed_candidate = MockEval.return_value.evaluate.call_args[0][0]
        assert passed_candidate is c
        assert passed_candidate.engine_class is BlobInspectionEngine

    # 11 ── PatternInspectionEngine dispatched via registry
    def test_engine_registry_dispatch_pattern(self):
        c = _make_candidate(PatternInspectionEngine, "Pattern")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        MockEval.return_value.evaluate.assert_called_once()
        passed_candidate = MockEval.return_value.evaluate.call_args[0][0]
        assert passed_candidate.engine_class is PatternInspectionEngine

    # 12 ── CircularCaliperInspectionEngine dispatched via registry
    def test_engine_registry_dispatch_circular(self):
        c = _make_candidate(CircularCaliperInspectionEngine, "Circular")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        MockEval.return_value.evaluate.assert_called_once()
        passed_candidate = MockEval.return_value.evaluate.call_args[0][0]
        assert passed_candidate.engine_class is CircularCaliperInspectionEngine

    # 13 ── LinearCaliperInspectionEngine dispatched via registry
    def test_engine_registry_dispatch_linear(self):
        c = _make_candidate(LinearCaliperInspectionEngine, "Linear")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        MockEval.return_value.evaluate.assert_called_once()
        passed_candidate = MockEval.return_value.evaluate.call_args[0][0]
        assert passed_candidate.engine_class is LinearCaliperInspectionEngine

    # 14 ── unknown engine_class is silently skipped and logged
    def test_unknown_engine_type_skipped(self):
        class _UnknownEngine:
            pass

        c_unknown = _make_candidate(_UnknownEngine, "UnknownEng")
        c_known = _make_candidate(BlobInspectionEngine, "Blob")

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            result = self.optimizer.run([c_unknown, c_known], OK_IMAGES, NG_IMAGES, SETTINGS)

        # evaluate called only for the known candidate
        MockEval.return_value.evaluate.assert_called_once()
        assert len(result.all_results) == 1
        combined = " ".join(result.optimization_log)
        assert "unknown" in combined.lower() or "UnknownEng" in combined

    # 15 ── empty candidate list raises ValueError
    def test_empty_candidate_list_raises(self):
        with pytest.raises(ValueError):
            self.optimizer.run([], OK_IMAGES, NG_IMAGES, SETTINGS)

    # 16 ── is_margin_warning propagates from EvaluationResult
    def test_margin_warning_propagated(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(
                80.0, is_margin_warning=True
            )
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert result.best_evaluation.is_margin_warning is True

    # 17 ── len(all_results) == number of known-engine candidates (unknown skipped)
    def test_optimization_result_all_results_length(self):
        class _UnknownEngine:
            pass

        c1 = _make_candidate(BlobInspectionEngine, "Blob")
        c2 = _make_candidate(PatternInspectionEngine, "Pattern")
        c3 = _make_candidate(_UnknownEngine, "Unknown")

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(70.0)
            result = self.optimizer.run([c1, c2, c3], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert len(result.all_results) == 2

    # 18 ── ng_images=[] handled gracefully (no crash)
    def test_no_ng_images_handled(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(50.0)
            result = self.optimizer.run([c], OK_IMAGES, [], SETTINGS)

        assert isinstance(result, OptimizationResult)

    # 19 ── tie in score: first candidate by insertion order wins
    def test_score_tie_deterministic(self):
        c1 = _make_candidate(BlobInspectionEngine, "Blob")
        c2 = _make_candidate(PatternInspectionEngine, "Pattern")

        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(75.0)
            result = self.optimizer.run([c1, c2], OK_IMAGES, NG_IMAGES, SETTINGS)

        assert result.best_candidate is c1

    # 20 ── log entries contain numeric score strings
    def test_log_contains_score_values(self):
        c = _make_candidate(BlobInspectionEngine, "Blob")
        with patch(_PATCH) as MockEval:
            MockEval.return_value.evaluate.return_value = _make_eval_result(82.5)
            result = self.optimizer.run([c], OK_IMAGES, NG_IMAGES, SETTINGS)

        combined = " ".join(result.optimization_log)
        assert "82.5" in combined or "82.50" in combined
