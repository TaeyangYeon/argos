"""
Tests for PatternInspectionEngine (Argos Step 37).

All images are generated with NumPy — no file I/O.

Synthetic images:
  ok_image  : 200×200 uniform gray (128)
  ng_clear  : ok with 60×60 white (255) rectangle at (70,70) — large clear defect
  ng_subtle : ok with 60×60 region having value 149 (diff=21) — below strict threshold
  ng_noise  : ok with scattered small blobs that morph_open filters out

Pass score = 5.0 % (defect_area / roi_area * 100).

For a 200×200 = 40 000 px image, 5 % = 2 000 px.
  - 60×60 = 3 600 px rectangle → 9 % > 5 % : detected by all candidates.
  - subtle diff=21 region: diff < strict threshold (30) → 0 % < 5 %: strict misses,
    diff > sensitive threshold (10) → ~9 % > 5 %: sensitive catches.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.models import InspectionResult, ROIConfig
from core.inspection.pattern_inspector import (
    PatternInspectionCandidate,
    PatternInspectionEngine,
    PASS_SCORE,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine() -> PatternInspectionEngine:
    return PatternInspectionEngine()


@pytest.fixture
def ok_image() -> np.ndarray:
    """200×200 uniform gray image (all pixels = 128)."""
    return np.full((200, 200), 128, dtype=np.uint8)


@pytest.fixture
def ng_image_clear(ok_image: np.ndarray) -> np.ndarray:
    """60×60 white (255) rectangle at (70,70) — defect area ratio ≈ 9 %."""
    ng = ok_image.copy()
    ng[70:130, 70:130] = 255
    return ng


@pytest.fixture
def ng_image_subtle(ok_image: np.ndarray) -> np.ndarray:
    """60×60 region with value 149 (diff=21).

    diff=21 is above sensitive threshold (10) but below strict threshold (30).
    After blurring the uniform reference stays 128; test interior stays ≈ 149.
    Sensitive detects ~3 600 px → 9 % ≥ 5 %;
    Strict sees 0 px above its threshold of 30.
    """
    ng = ok_image.copy()
    ng[70:130, 70:130] = 149  # diff = 21
    return ng


@pytest.fixture
def ng_image_noise(ok_image: np.ndarray) -> np.ndarray:
    """Scattered 3×3 blobs that survive GaussianBlur but are small (<50 px each)."""
    ng = ok_image.copy()
    # Three isolated 3×3 blobs — each ≈ 1–4 px after blur+threshold
    for r, c in [(10, 10), (100, 100), (180, 180)]:
        ng[r : r + 3, c : c + 3] = 255
    return ng


@pytest.fixture
def full_roi() -> ROIConfig:
    return ROIConfig(x=0, y=0, width=200, height=200)


@pytest.fixture
def candidates(engine, ok_image, ng_image_clear) -> list[PatternInspectionCandidate]:
    return engine.generate_candidates([ok_image], [ng_image_clear])


@pytest.fixture
def strict_candidate(candidates) -> PatternInspectionCandidate:
    return candidates[0]


@pytest.fixture
def balanced_candidate(candidates) -> PatternInspectionCandidate:
    return candidates[1]


@pytest.fixture
def sensitive_candidate(candidates) -> PatternInspectionCandidate:
    return candidates[2]


# ─── 1. generate_candidates ──────────────────────────────────────────────────

def test_generate_candidates_returns_three(engine, ok_image, ng_image_clear):
    """generate_candidates must return exactly 3 candidates."""
    result = engine.generate_candidates([ok_image], [ng_image_clear])
    assert len(result) == 3


def test_candidate_ids_are_unique(candidates):
    """Each candidate must have a distinct candidate_id."""
    ids = [c.candidate_id for c in candidates]
    assert len(ids) == len(set(ids))


def test_candidate_thresholds_differ(candidates):
    """Strict > balanced > sensitive threshold."""
    t0, t1, t2 = [c.threshold for c in candidates]
    assert t0 > t1 > t2


def test_candidate_min_areas_differ(candidates):
    """Strict > balanced > sensitive min_area."""
    a0, a1, a2 = [c.min_area for c in candidates]
    assert a0 > a1 > a2


def test_candidates_are_dataclass_instances(candidates):
    for c in candidates:
        assert isinstance(c, PatternInspectionCandidate)


def test_generate_candidates_design_doc_not_empty(candidates):
    """Every candidate must have a non-empty design_doc."""
    for c in candidates:
        assert c.design_doc, f"design_doc is empty for {c.candidate_id}"


# ─── 2. design_doc structure ─────────────────────────────────────────────────

def test_design_doc_has_four_sections(candidates):
    """design_doc must contain exactly the four required Korean-key sections."""
    required = {"배치구조", "개별파라미터", "결과계산", "선택근거"}
    for c in candidates:
        assert set(c.design_doc.keys()) == required, (
            f"Candidate {c.candidate_id}: keys={set(c.design_doc.keys())}"
        )


def test_design_doc_배치구조_has_required_keys(candidates):
    for c in candidates:
        section = c.design_doc["배치구조"]
        assert "검사_유형" in section
        assert "비교_방법" in section


def test_design_doc_개별파라미터_has_threshold(candidates):
    for c in candidates:
        params = c.design_doc["개별파라미터"]
        assert "threshold" in params
        assert params["threshold"] == c.threshold


def test_design_doc_결과계산_has_formula(candidates):
    for c in candidates:
        calc = c.design_doc["결과계산"]
        assert "점수_공식" in calc


def test_design_doc_선택근거_has_rationale(candidates):
    for c in candidates:
        rationale = c.design_doc["선택근거"]
        assert "선택_이유" in rationale


# ─── 3. library_mapping structure ────────────────────────────────────────────

def test_library_mapping_has_four_vendors(candidates):
    """Every concept in library_mapping must have Keyence, Cognex, Halcon, MIL."""
    required_vendors = {"Keyence", "Cognex", "Halcon", "MIL"}
    for c in candidates:
        for concept, vendors in c.library_mapping.items():
            assert set(vendors.keys()) == required_vendors, (
                f"Candidate {c.candidate_id}, concept '{concept}': "
                f"vendors={set(vendors.keys())}"
            )


def test_library_mapping_has_four_concepts(candidates):
    """library_mapping must contain exactly four concept entries."""
    for c in candidates:
        assert len(c.library_mapping) == 4, (
            f"Expected 4 concepts, got {len(c.library_mapping)}"
        )


# ─── 4. _compute_diff_score ──────────────────────────────────────────────────

def test_compute_diff_score_identical_images_returns_zero(engine, ok_image):
    """Identical OK images: diff = 0 everywhere → score must be 0."""
    score = engine._compute_diff_score(ok_image, ok_image.copy(), threshold=10, min_area=1)
    assert score == pytest.approx(0.0, abs=1e-6)


def test_compute_diff_score_different_images_returns_positive(
    engine, ok_image, ng_image_clear
):
    """OK vs clear NG: score must be strictly positive."""
    score = engine._compute_diff_score(ok_image, ng_image_clear, threshold=10, min_area=1)
    assert score > 0.0


def test_compute_diff_score_respects_roi(engine, ok_image):
    """Defect outside ROI must not contribute to score."""
    # Defect at (150, 150) — outside ROI (0,0,100,100)
    ng_outside = ok_image.copy()
    ng_outside[150:180, 150:180] = 255
    roi = ROIConfig(x=0, y=0, width=100, height=100)
    score = engine._compute_diff_score(ok_image, ng_outside, threshold=10, min_area=1, roi=roi)
    assert score == pytest.approx(0.0, abs=1e-6)


def test_compute_diff_score_threshold_effect(engine, ok_image, ng_image_clear):
    """Higher threshold must produce a score <= lower threshold (fewer pixels)."""
    score_low  = engine._compute_diff_score(ok_image, ng_image_clear, threshold=10, min_area=1)
    score_high = engine._compute_diff_score(ok_image, ng_image_clear, threshold=30, min_area=1)
    assert score_low >= score_high


def test_compute_diff_score_min_area_filter(engine, ok_image):
    """Large min_area must filter small blobs, reducing score to 0."""
    # 30×30 white rectangle — area ≈ 900 px (well below min_area=2000)
    ng_small = ok_image.copy()
    ng_small[85:115, 85:115] = 255

    score_no_filter  = engine._compute_diff_score(ok_image, ng_small, threshold=10, min_area=1)
    score_large_min  = engine._compute_diff_score(ok_image, ng_small, threshold=10, min_area=2000)

    # Small defect survives with min_area=1 but filtered with min_area=2000
    assert score_no_filter > 0.0
    assert score_large_min == pytest.approx(0.0, abs=1e-6)


def test_compute_diff_score_roi_none_uses_full_image(engine, ok_image, ng_image_clear):
    """roi=None must process the entire image, consistent with full-image ROI."""
    score_none = engine._compute_diff_score(ok_image, ng_image_clear, threshold=10, min_area=1, roi=None)
    roi_full   = ROIConfig(x=0, y=0, width=200, height=200)
    score_full = engine._compute_diff_score(ok_image, ng_image_clear, threshold=10, min_area=1, roi=roi_full)
    assert score_none == pytest.approx(score_full, abs=0.5)


# ─── 5. run() ────────────────────────────────────────────────────────────────

def test_run_returns_inspection_result(engine, balanced_candidate, ok_image, ng_image_clear):
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert isinstance(result, InspectionResult)


def test_run_returns_overlay_image(engine, balanced_candidate, ok_image, ng_image_clear):
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert result.overlay_image is not None
    assert isinstance(result.overlay_image, np.ndarray)


def test_run_overlay_image_is_color(engine, balanced_candidate, ok_image, ng_image_clear):
    """Overlay image must be a 3-channel BGR array."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert result.overlay_image.ndim == 3
    assert result.overlay_image.shape[2] == 3


def test_run_ok_images_pass(engine, balanced_candidate, ok_image, ng_image_clear):
    """All identical OK images must score below PASS_SCORE → ok_pass_rate = 1.0."""
    ok_images = [ok_image, ok_image.copy(), ok_image.copy()]
    result = engine.run(balanced_candidate, ok_images, [ng_image_clear])
    # ok_pass_rate is embedded in the score: score = (ok_pass_rate + ng_rate)/2
    # We verify indirectly: score must reflect a high ok_pass_rate
    # For ok_pass_rate=1.0, ng_rate=1.0 → score=1.0
    assert result.score > 0.5


def test_run_ng_images_detected(engine, balanced_candidate, ok_image, ng_image_clear):
    """Large clear defect must be detected by balanced candidate."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    # For clear NG (diff=127 >> threshold=20), score must be ≥ 5 % → detected
    ng_score = engine._compute_diff_score(
        ok_image, ng_image_clear, balanced_candidate.threshold, balanced_candidate.min_area
    )
    assert ng_score >= PASS_SCORE


def test_run_separation_score_positive(engine, balanced_candidate, ok_image, ng_image_clear):
    """ok_pass_rate + ng_detection_rate > 1.0 for well-separated images."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert result.score > 0.5  # score = (ok_pass + ng_det)/2 > 0.5 means sum > 1


def test_run_empty_ng_raises(engine, balanced_candidate, ok_image):
    with pytest.raises(ValueError, match="NG"):
        engine.run(balanced_candidate, [ok_image], [])


def test_run_empty_ok_raises(engine, balanced_candidate, ng_image_clear):
    with pytest.raises(ValueError, match="OK"):
        engine.run(balanced_candidate, [], [ng_image_clear])


def test_run_roi_none_uses_full_image(engine, balanced_candidate, ok_image, ng_image_clear):
    """roi=None must not raise and must return a valid InspectionResult."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear], roi=None)
    assert isinstance(result, InspectionResult)
    assert result.success is True


def test_run_result_success_flag(engine, balanced_candidate, ok_image, ng_image_clear):
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert result.success is True


def test_run_strategy_name(engine, balanced_candidate, ok_image, ng_image_clear):
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert result.strategy_name == "PatternInspection"


def test_run_best_candidate_set(engine, balanced_candidate, ok_image, ng_image_clear):
    """run() must set best_candidate to the evaluated candidate."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    assert result.best_candidate is balanced_candidate


# ─── 6. Candidate sensitivity comparison ─────────────────────────────────────

def test_run_strict_candidate_lower_ng_detection(
    engine, ok_image, ng_image_subtle, candidates
):
    """Strict candidate (threshold=30) must not detect subtle NG (diff=21).

    Sensitive candidate (threshold=10) must detect the same subtle NG.
    Therefore strict_ng_rate < sensitive_ng_rate.
    """
    strict_c    = candidates[0]  # threshold=30
    sensitive_c = candidates[2]  # threshold=10

    strict_score    = engine._compute_diff_score(
        ok_image, ng_image_subtle, strict_c.threshold, strict_c.min_area
    )
    sensitive_score = engine._compute_diff_score(
        ok_image, ng_image_subtle, sensitive_c.threshold, sensitive_c.min_area
    )

    # Strict should miss (diff=21 < threshold=30 → score=0)
    assert strict_score < PASS_SCORE, (
        f"Strict should not detect subtle NG, got score={strict_score:.2f}"
    )
    # Sensitive should catch (diff=21 > threshold=10 → score ≥ 5%)
    assert sensitive_score >= PASS_SCORE, (
        f"Sensitive should detect subtle NG, got score={sensitive_score:.2f}"
    )


def test_run_sensitive_candidate_higher_ng_recall(
    engine, ok_image, ng_image_subtle, candidates
):
    """Sensitive candidate detects subtle NG that strict candidate misses."""
    strict_c    = candidates[0]  # threshold=30
    sensitive_c = candidates[2]  # threshold=10

    # Run full evaluation with subtle NG
    result_strict    = engine.run(strict_c,    [ok_image], [ng_image_subtle])
    result_sensitive = engine.run(sensitive_c, [ok_image], [ng_image_subtle])

    # score = (ok_pass_rate + ng_detection_rate) / 2
    # ok_pass_rate should be 1.0 for both (identical ok vs ok)
    # For strict: ng_detection_rate=0.0 → score=0.5
    # For sensitive: ng_detection_rate=1.0 → score=1.0
    assert result_sensitive.score > result_strict.score


def test_strict_threshold_higher_than_sensitive(candidates):
    """Explicit check: strict.threshold > sensitive.threshold."""
    assert candidates[0].threshold > candidates[2].threshold


def test_sensitive_min_area_lower_than_strict(candidates):
    """Explicit check: sensitive.min_area < strict.min_area."""
    assert candidates[2].min_area < candidates[0].min_area


# ─── 7. Overlay correctness ───────────────────────────────────────────────────

def test_overlay_shape_matches_input(engine, balanced_candidate, ok_image, ng_image_clear):
    """Overlay image height and width must match input image dimensions."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    h, w = ok_image.shape[:2]
    assert result.overlay_image.shape[0] == h
    assert result.overlay_image.shape[1] == w


def test_overlay_contains_red_pixels(engine, balanced_candidate, ok_image, ng_image_clear):
    """For a clear NG, at least some pixels in the overlay must be marked red."""
    result = engine.run(balanced_candidate, [ok_image], [ng_image_clear])
    overlay = result.overlay_image
    # Red in BGR: B=0, G=0, R=255 → check channel 2 (R) for 255 pixels
    red_pixels = np.sum(overlay[:, :, 2] == 255)
    assert red_pixels > 0, "No red defect pixels found in overlay"
