"""
Tests for core/evaluation/evaluator.py — InspectionEvaluator (Step 39).

All tests use synthetic numpy arrays (no real image I/O) and a configurable
MockEngine class.  Real inspection engines are never imported here.

Coverage:
  - Normal scoring (perfect, zero, partial)
  - Weighted score formula verification
  - Margin calculation and warning boundary
  - Empty OK / empty NG / both empty graceful handling
  - Single-image-per-class
  - Per-image exception isolation
  - FP / FN list population
  - Score vs. threshold comparison
  - Custom weights
  - Engine name pass-through
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pytest

from core.evaluation.evaluator import InspectionEvaluator
from core.models import EvaluationResult, InspectionCandidate
from core.inspection.candidate_generator import EngineCandidate


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — synthetic images and mock engine factories
# ─────────────────────────────────────────────────────────────────────────────

def _gray(value: int = 128, size: tuple = (64, 64)) -> np.ndarray:
    """Return a solid-gray uint8 numpy image."""
    return np.full(size, value, dtype=np.uint8)


def _make_candidate_result(ok_pass_rate: float, ng_detect_rate: float) -> list[InspectionCandidate]:
    """Build a minimal list[InspectionCandidate] for mock engine returns."""
    score = (ok_pass_rate + ng_detect_rate) / 2.0
    return [
        InspectionCandidate(
            candidate_id="mock_0",
            method="mock",
            params={},
            design_doc={},
            library_mapping={},
            ok_pass_rate=ok_pass_rate,
            ng_detect_rate=ng_detect_rate,
            score=score,
            rationale="mock",
        )
    ]


def make_mock_engine_class(
    ok_pass_rate: float = 1.0,
    ng_detect_rate: float = 1.0,
    raise_on_ok_indices: Optional[set] = None,
    raise_on_ng_indices: Optional[set] = None,
) -> type:
    """
    Factory that returns a fresh MockEngine *class* with the given behavior.

    Each call returns a class (not instance) so it can be passed as
    EngineCandidate.engine_class and instantiated by the evaluator.

    Args:
        ok_pass_rate:         Rate returned when engine is called in OK mode.
        ng_detect_rate:       Rate returned when engine is called in NG mode.
        raise_on_ok_indices:  Set of call-order indices (0-based) for which
                              the OK-mode call raises RuntimeError.
        raise_on_ng_indices:  Set of call-order indices for NG-mode raises.
    """
    _ok_raises = raise_on_ok_indices or set()
    _ng_raises = raise_on_ng_indices or set()
    _configured_ok_rate = ok_pass_rate
    _configured_ng_rate = ng_detect_rate

    class MockEngine:
        def __init__(self) -> None:
            self._ok_call_idx = 0
            self._ng_call_idx = 0

        def run(
            self,
            ok_images: list,
            ng_images: Optional[list] = None,
            roi=None,
            purpose=None,
        ) -> list[InspectionCandidate]:
            ng_images = ng_images or []
            is_ng_mode = bool(ng_images)

            if is_ng_mode:
                idx = self._ng_call_idx
                self._ng_call_idx += 1
                if idx in _ng_raises:
                    raise RuntimeError(f"Simulated NG error at call {idx}")
                return _make_candidate_result(1.0, _configured_ng_rate)
            else:
                idx = self._ok_call_idx
                self._ok_call_idx += 1
                if idx in _ok_raises:
                    raise RuntimeError(f"Simulated OK error at call {idx}")
                return _make_candidate_result(_configured_ok_rate, 0.0)

        def get_strategy_name(self) -> str:
            return "MockEngine"

    return MockEngine


def make_candidate(
    engine_class: type,
    engine_name: str = "Mock Engine",
    priority: float = 0.8,
) -> EngineCandidate:
    """Convenience wrapper to build an EngineCandidate for tests."""
    return EngineCandidate(
        engine_class=engine_class,
        engine_name=engine_name,
        priority=priority,
        rationale="test candidate",
        source="rule_based",
    )


@dataclass
class FakeSettings:
    """Minimal settings stand-in with only fields used by InspectionEvaluator."""
    w1: float = 0.5
    w2: float = 0.5
    score_threshold: float = 70.0
    margin_warning: float = 15.0


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def evaluator() -> InspectionEvaluator:
    return InspectionEvaluator()


@pytest.fixture
def default_settings() -> FakeSettings:
    return FakeSettings()


@pytest.fixture
def ok_images() -> list[np.ndarray]:
    return [_gray(200) for _ in range(5)]


@pytest.fixture
def ng_images() -> list[np.ndarray]:
    return [_gray(50) for _ in range(5)]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Normal scoring — perfect case
# ─────────────────────────────────────────────────────────────────────────────

def test_perfect_score_returns_100(evaluator, ok_images, ng_images, default_settings):
    """All OK pass + all NG detected → final_score == 100.0"""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), ok_images, ng_images, default_settings)
    assert result.final_score == pytest.approx(100.0)


def test_zero_score_returns_0(evaluator, ok_images, ng_images, default_settings):
    """All OK fail + no NG detected → final_score == 0.0"""
    cls = make_mock_engine_class(ok_pass_rate=0.0, ng_detect_rate=0.0)
    result = evaluator.evaluate(make_candidate(cls), ok_images, ng_images, default_settings)
    assert result.final_score == pytest.approx(0.0)


def test_ok_pass_rate_partial(evaluator, default_settings):
    """4 out of 5 OK images pass → ok_pass_rate == 0.8"""
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(2)]
    # Make the 3rd OK call (index 2) fail → 4/5 pass
    cls = make_mock_engine_class(ok_pass_rate=0.0, raise_on_ok_indices={2})
    # All other OK calls will also be ok_pass_rate=0.0... we need a different approach.
    # Use ok_pass_rate=1.0 for passing images and raise for index 2.
    cls2 = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0, raise_on_ok_indices={2})
    result = evaluator.evaluate(make_candidate(cls2), ok_imgs, ng_imgs, default_settings)
    # 4 pass, 1 fails (exception → False) → 4/5 = 0.8
    assert result.ok_pass_rate == pytest.approx(0.8)


def test_ng_detect_rate_partial(evaluator, default_settings):
    """3 out of 5 NG images detected → ng_detect_rate == 0.6"""
    ok_imgs = [_gray() for _ in range(3)]
    ng_imgs = [_gray() for _ in range(5)]
    # NG calls at indices 1 and 3 raise → those are treated as undetected
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0, raise_on_ng_indices={1, 3})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    # 3 detected, 2 fail (exception → False) → 3/5 = 0.6
    assert result.ng_detect_rate == pytest.approx(0.6)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Weighted score formula
# ─────────────────────────────────────────────────────────────────────────────

def test_weighted_score_formula_equal_weights(evaluator, default_settings):
    """Formula: (ok_pass_rate * 0.5 + ng_detect_rate * 0.5) * 100"""
    ok_imgs = [_gray() for _ in range(4)]
    ng_imgs = [_gray() for _ in range(4)]
    # ok_pass_rate = 1.0, ng_detect_rate = 1.0 → should be 100
    # but we want a mid-point: make 2/4 OK raise (ok_pass_rate=0.5), all NG pass
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0, raise_on_ok_indices={0, 1})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    expected = (0.5 * 0.5 + 1.0 * 0.5) * 100.0
    assert result.final_score == pytest.approx(expected)


def test_weighted_score_formula_ok_only(evaluator):
    """w1=1.0, w2=0.0 → final_score driven entirely by ok_pass_rate"""
    settings = FakeSettings(w1=1.0, w2=0.0)
    ok_imgs = [_gray() for _ in range(4)]
    ng_imgs = [_gray() for _ in range(4)]
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=0.0, raise_on_ok_indices={0})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, settings)
    expected = (0.75 * 1.0 + 0.0 * 0.0) * 100.0
    assert result.final_score == pytest.approx(expected)


def test_weighted_score_formula_ng_only(evaluator):
    """w1=0.0, w2=1.0 → final_score driven entirely by ng_detect_rate"""
    settings = FakeSettings(w1=0.0, w2=1.0)
    ok_imgs = [_gray() for _ in range(3)]
    ng_imgs = [_gray() for _ in range(4)]
    cls = make_mock_engine_class(ok_pass_rate=0.0, ng_detect_rate=1.0, raise_on_ng_indices={0})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, settings)
    expected = (0.0 * 0.0 + 0.75 * 1.0) * 100.0
    assert result.final_score == pytest.approx(expected)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Margin calculation and warning
# ─────────────────────────────────────────────────────────────────────────────

def test_margin_formula_correctness(evaluator, default_settings):
    """margin = (ok_pass_rate + ng_detect_rate - 1.0) * 100"""
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(5)]
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    expected_margin = (1.0 + 1.0 - 1.0) * 100.0  # 100.0
    assert result.margin == pytest.approx(expected_margin)


def test_margin_warning_triggered_below_15(evaluator, default_settings):
    """margin < 15 → is_margin_warning == True"""
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(5)]
    # ok_pass_rate=1.0, ng_detect_rate raises on 4 of 5 → ng_detect_rate=0.2
    # margin = (1.0 + 0.2 - 1.0) * 100 = 20... not below 15
    # Use ok_pass_rate raising too: ok_pass_rate=0.6, ng_detect_rate=0.2
    # margin = (0.6 + 0.2 - 1.0) * 100 = -20 → warning
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ok_indices={0, 1}, raise_on_ng_indices={0, 1, 2, 3})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    # ok_pass_rate = 3/5 = 0.6, ng_detect_rate = 1/5 = 0.2
    # margin = (0.6 + 0.2 - 1.0) * 100 = -20 < 15
    assert result.is_margin_warning is True


def test_margin_warning_not_triggered_above_15(evaluator, default_settings):
    """margin ≥ 15 → is_margin_warning == False"""
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(5)]
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    # margin = 100.0 ≥ 15 → no warning
    assert result.is_margin_warning is False


def test_margin_boundary_exactly_at_threshold(evaluator):
    """margin == margin_warning exactly → is_margin_warning == False (not strictly <)

    Uses values with exact IEEE-754 binary representations to avoid float issues:
      ok_pass_rate = 1.0  (2 OK, 0 failures)
      ng_detect_rate = 0.25  (4 NG, 3 raise → 1/4 exact)
      margin = (1.0 + 0.25 - 1.0) * 100 = 25.0  (exact)
      margin_warning = 25.0  →  25.0 < 25.0 is False  →  no warning
    """
    settings = FakeSettings(margin_warning=25.0)
    ok_imgs = [_gray() for _ in range(2)]
    ng_imgs = [_gray() for _ in range(4)]
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ng_indices={0, 1, 2})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, settings)
    # ok_pass_rate = 2/2 = 1.0, ng_detect_rate = 1/4 = 0.25 (exact in IEEE-754)
    # margin = (1.0 + 0.25 - 1.0) * 100 = 25.0 exactly → NOT < 25.0 → no warning
    assert result.margin == pytest.approx(25.0)
    assert result.is_margin_warning is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. Empty image list handling
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_ng_images_warns(evaluator, ok_images, default_settings):
    """Empty NG list → UserWarning emitted, ng_detect_rate defaults to 1.0"""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = evaluator.evaluate(make_candidate(cls), ok_images, [], default_settings)
    assert any("NG" in str(w.message) for w in caught)
    assert result.ng_detect_rate == pytest.approx(1.0)


def test_empty_ok_images_warns(evaluator, ng_images, default_settings):
    """Empty OK list → UserWarning emitted, ok_pass_rate defaults to 1.0"""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=0.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = evaluator.evaluate(make_candidate(cls), [], ng_images, default_settings)
    assert any("OK" in str(w.message) for w in caught)
    assert result.ok_pass_rate == pytest.approx(1.0)


def test_both_empty_images_returns_valid_result(evaluator, default_settings):
    """Both lists empty → valid EvaluationResult returned (no crash)"""
    cls = make_mock_engine_class()
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = evaluator.evaluate(make_candidate(cls), [], [], default_settings)
    assert isinstance(result, EvaluationResult)
    # Both default to 1.0 → final_score = 100.0
    assert result.final_score == pytest.approx(100.0)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Single image per class
# ─────────────────────────────────────────────────────────────────────────────

def test_single_ok_image_passes(evaluator, default_settings):
    """Single OK image that passes → ok_pass_rate == 1.0"""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), [_gray()], [_gray()], default_settings)
    assert result.ok_pass_rate == pytest.approx(1.0)


def test_single_ng_image_detected(evaluator, default_settings):
    """Single NG image detected → ng_detect_rate == 1.0"""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), [_gray()], [_gray()], default_settings)
    assert result.ng_detect_rate == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Per-image exception isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_ok_exception_isolation_does_not_abort(evaluator, default_settings):
    """One failing OK image must not abort evaluation of remaining OK images."""
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(3)]
    # Image at index 2 raises; the other 4 pass → ok_pass_rate = 4/5 = 0.8
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0, raise_on_ok_indices={2})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    assert result.ok_pass_rate == pytest.approx(0.8)
    assert result.ng_detect_rate == pytest.approx(1.0)


def test_ng_exception_isolation_does_not_abort(evaluator, default_settings):
    """One failing NG image must not abort evaluation of remaining NG images."""
    ok_imgs = [_gray() for _ in range(3)]
    ng_imgs = [_gray() for _ in range(5)]
    # NG at index 0 raises; the other 4 detect → ng_detect_rate = 4/5 = 0.8
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0, raise_on_ng_indices={0})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    assert result.ng_detect_rate == pytest.approx(0.8)
    assert result.ok_pass_rate == pytest.approx(1.0)


def test_all_ok_exceptions_gives_zero_pass_rate(evaluator, default_settings):
    """All OK images raise → ok_pass_rate == 0.0"""
    ok_imgs = [_gray() for _ in range(3)]
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ok_indices={0, 1, 2})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, [_gray()], default_settings)
    assert result.ok_pass_rate == pytest.approx(0.0)


def test_all_ng_exceptions_gives_zero_detect_rate(evaluator, default_settings):
    """All NG images raise → ng_detect_rate == 0.0"""
    ng_imgs = [_gray() for _ in range(3)]
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ng_indices={0, 1, 2})
    result = evaluator.evaluate(make_candidate(cls), [_gray()], ng_imgs, default_settings)
    assert result.ng_detect_rate == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 7. FP / FN tracking
# ─────────────────────────────────────────────────────────────────────────────

def test_fp_images_contains_failed_ok_indices(evaluator, default_settings):
    """OK images that fail are recorded in fp_images with 'ok_{i}' keys."""
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(2)]
    # Images at index 1 and 3 fail (raise)
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ok_indices={1, 3})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    assert "ok_1" in result.fp_images
    assert "ok_3" in result.fp_images
    assert len(result.fp_images) == 2


def test_fn_images_contains_missed_ng_indices(evaluator, default_settings):
    """NG images that are missed are recorded in fn_images with 'ng_{j}' keys."""
    ok_imgs = [_gray() for _ in range(3)]
    ng_imgs = [_gray() for _ in range(5)]
    # NG at indices 2 and 4 raise → missed
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ng_indices={2, 4})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, default_settings)
    assert "ng_2" in result.fn_images
    assert "ng_4" in result.fn_images
    assert len(result.fn_images) == 2


def test_perfect_run_has_empty_fp_fn_lists(evaluator, ok_images, ng_images, default_settings):
    """Perfect evaluation → no FP or FN images recorded."""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), ok_images, ng_images, default_settings)
    assert result.fp_images == []
    assert result.fn_images == []


# ─────────────────────────────────────────────────────────────────────────────
# 8. Score vs. threshold + custom weights
# ─────────────────────────────────────────────────────────────────────────────

def test_score_below_threshold_is_detectable(evaluator):
    """final_score < score_threshold is detectable via the returned value."""
    settings = FakeSettings(score_threshold=70.0, w1=0.5, w2=0.5)
    ok_imgs = [_gray() for _ in range(5)]
    ng_imgs = [_gray() for _ in range(5)]
    # ok_pass_rate=0.6, ng_detect_rate=0.6 → score = (0.6*0.5 + 0.6*0.5)*100 = 60 < 70
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ok_indices={0, 1}, raise_on_ng_indices={0, 1})
    result = evaluator.evaluate(make_candidate(cls), ok_imgs, ng_imgs, settings)
    assert result.final_score < settings.score_threshold


def test_score_above_threshold_is_detectable(evaluator, ok_images, ng_images):
    """final_score ≥ score_threshold is detectable via the returned value."""
    settings = FakeSettings(score_threshold=70.0, w1=0.5, w2=0.5)
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), ok_images, ng_images, settings)
    assert result.final_score >= settings.score_threshold


def test_custom_weights_affect_score(evaluator, ok_images, ng_images):
    """Different w1/w2 combinations yield different final scores."""
    settings_a = FakeSettings(w1=0.9, w2=0.1)
    settings_b = FakeSettings(w1=0.1, w2=0.9)
    # ok_pass_rate=0.8, ng_detect_rate=0.4 → different final scores for a vs b
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                  raise_on_ok_indices={0}, raise_on_ng_indices={0, 1, 2})
    result_a = evaluator.evaluate(make_candidate(cls), ok_images, ng_images, settings_a)
    cls2 = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0,
                                   raise_on_ok_indices={0}, raise_on_ng_indices={0, 1, 2})
    result_b = evaluator.evaluate(make_candidate(cls2), ok_images, ng_images, settings_b)
    # With w1=0.9 (OK weight high) and ok_pass_rate=0.8, score_a should be higher
    assert result_a.final_score != pytest.approx(result_b.final_score)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Engine name and get_score()
# ─────────────────────────────────────────────────────────────────────────────

def test_best_strategy_matches_candidate_name(evaluator, ok_images, ng_images, default_settings):
    """EvaluationResult.best_strategy must equal the candidate's engine_name."""
    cls = make_mock_engine_class()
    candidate = make_candidate(cls, engine_name="TestEngine")
    result = evaluator.evaluate(candidate, ok_images, ng_images, default_settings)
    assert result.best_strategy == "TestEngine"


def test_get_score_returns_last_final_score(evaluator, ok_images, ng_images, default_settings):
    """get_score() must return the same value as the last EvaluationResult.final_score."""
    cls = make_mock_engine_class(ok_pass_rate=1.0, ng_detect_rate=1.0)
    result = evaluator.evaluate(make_candidate(cls), ok_images, ng_images, default_settings)
    assert evaluator.get_score() == pytest.approx(result.final_score)


def test_get_score_initial_value_is_zero(evaluator):
    """get_score() returns 0.0 before any evaluate() call."""
    assert evaluator.get_score() == pytest.approx(0.0)
