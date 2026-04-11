"""
Tests for BlobInspectionEngine (Step 33).

Uses synthetic images only — no file I/O required.
Minimum 12 tests as specified.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.exceptions import InputValidationError
from core.inspection.blob_inspector import BlobInspectionEngine
from core.models import InspectionCandidate, ROIConfig


# ─── Synthetic image helpers ──────────────────────────────────────────────────

def _black(h: int = 100, w: int = 100) -> np.ndarray:
    """Pure black image (no blobs)."""
    return np.zeros((h, w), dtype=np.uint8)


def _with_circle(
    h: int = 100, w: int = 100, cx: int = 50, cy: int = 50, r: int = 15
) -> np.ndarray:
    """Black image with a single white circle (clean blob)."""
    img = _black(h, w)
    cv2 = __import__("cv2")
    cv2.circle(img, (cx, cy), r, 255, -1)
    return img


def _with_two_circles(h: int = 100, w: int = 100) -> np.ndarray:
    """Black image with two white circles."""
    img = _black(h, w)
    cv2 = __import__("cv2")
    cv2.circle(img, (25, 50), 10, 255, -1)
    cv2.circle(img, (75, 50), 10, 255, -1)
    return img


def _with_rect(h: int = 100, w: int = 100) -> np.ndarray:
    """Black image with a white rectangle (low circularity)."""
    img = _black(h, w)
    cv2 = __import__("cv2")
    cv2.rectangle(img, (10, 10), (90, 30), 255, -1)
    return img


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine() -> BlobInspectionEngine:
    return BlobInspectionEngine()


@pytest.fixture
def ok_images() -> list[np.ndarray]:
    return [_with_circle(), _with_circle(cx=48, cy=52)]


@pytest.fixture
def ng_images() -> list[np.ndarray]:
    return [_with_two_circles(), _black()]


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestBlobInspectionEngineBasic:
    """Basic structural and sorting tests."""

    def test_returns_three_candidates(self, engine, ok_images, ng_images):
        """Engine must return exactly 3 candidates."""
        candidates = engine.run(ok_images, ng_images)
        assert len(candidates) == 3

    def test_candidates_sorted_by_score_descending(self, engine, ok_images, ng_images):
        """Candidates must be ordered from highest to lowest score."""
        candidates = engine.run(ok_images, ng_images)
        scores = [c.score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_all_candidate_fields_present(self, engine, ok_images, ng_images):
        """Every required field must be present and non-None."""
        candidates = engine.run(ok_images, ng_images)
        required_fields = [
            "candidate_id", "method", "params", "design_doc",
            "library_mapping", "score",
        ]
        for c in candidates:
            for field in required_fields:
                assert hasattr(c, field), f"Missing field: {field}"
                assert getattr(c, field) is not None, f"Field is None: {field}"

    def test_candidate_method_is_blob(self, engine, ok_images, ng_images):
        """All candidates must have method == 'blob'."""
        for c in engine.run(ok_images, ng_images):
            assert c.method == "blob"

    def test_candidate_ids_unique(self, engine, ok_images, ng_images):
        """candidate_id must be unique across candidates."""
        ids = [c.candidate_id for c in engine.run(ok_images, ng_images)]
        assert len(ids) == len(set(ids))


class TestDesignDoc:
    """Four-section design document structure tests."""

    def test_design_doc_has_exactly_four_keys(self, engine, ok_images, ng_images):
        """design_doc must have exactly 4 sections."""
        for c in engine.run(ok_images, ng_images):
            assert set(c.design_doc.keys()) == {
                "layout", "parameters", "result_calculation", "rationale"
            }, f"design_doc keys: {list(c.design_doc.keys())}"

    def test_library_mapping_has_required_keys(self, engine, ok_images, ng_images):
        """library_mapping must include keyence, cognex, halcon, mil."""
        for c in engine.run(ok_images, ng_images):
            assert set(c.library_mapping.keys()) == {"keyence", "cognex", "halcon", "mil"}


class TestRates:
    """Numeric rate / score correctness tests."""

    def test_ok_pass_rate_in_valid_range(self, engine, ok_images, ng_images):
        """ok_pass_rate must be in [0.0, 1.0]."""
        for c in engine.run(ok_images, ng_images):
            assert 0.0 <= c.ok_pass_rate <= 1.0

    def test_ng_detect_rate_in_valid_range(self, engine, ok_images, ng_images):
        """ng_detect_rate must be in [0.0, 1.0]."""
        for c in engine.run(ok_images, ng_images):
            assert 0.0 <= c.ng_detect_rate <= 1.0

    def test_score_formula_correct(self, engine, ok_images, ng_images):
        """score == ok_pass_rate * 0.5 + ng_detect_rate * 0.5 within tolerance."""
        for c in engine.run(ok_images, ng_images):
            expected = c.ok_pass_rate * 0.5 + c.ng_detect_rate * 0.5
            assert abs(c.score - expected) < 0.001, (
                f"score mismatch for {c.candidate_id}: "
                f"score={c.score}, expected={expected}"
            )


class TestEdgeCases:
    """Edge-case and error-handling tests."""

    def test_empty_ng_list_gives_zero_ng_detect_rate(self, engine, ok_images):
        """Empty NG list must not raise and must set ng_detect_rate == 0.0."""
        candidates = engine.run(ok_images, ng_images=[])
        for c in candidates:
            assert c.ng_detect_rate == 0.0

    def test_empty_ng_list_does_not_raise(self, engine, ok_images):
        """engine.run() with empty ng_images must not raise any exception."""
        engine.run(ok_images, ng_images=[])  # must not raise

    def test_empty_ok_list_raises_input_validation_error(self, engine, ng_images):
        """Empty OK list must raise InputValidationError."""
        with pytest.raises(InputValidationError):
            engine.run(ok_images=[], ng_images=ng_images)

    def test_roi_crop_does_not_crash(self, engine, ng_images):
        """Providing a valid ROI must not cause any crash."""
        ok = [_with_circle(h=200, w=200, cx=100, cy=100, r=20)]
        roi = ROIConfig(x=50, y=50, width=100, height=100)
        candidates = engine.run(ok_images=ok, ng_images=ng_images, roi=roi)
        assert len(candidates) == 3


class TestPresetOrdering:
    """Preset-specific parameter ordering tests."""

    def test_candidate_a_has_tighter_area_min_than_candidate_c(
        self, engine, ok_images, ng_images
    ):
        """
        Candidate A (strict) must have a larger area_min than Candidate C (loose).
        'Tighter' means a higher minimum area threshold — small blobs are rejected,
        reducing false positives from noise.  Candidate C is permissive (low area_min)
        to maximise recall.
        """
        candidates = engine.run(ok_images, ng_images)
        # Find by id suffix, independent of score-based sort order
        cand_a = next(c for c in candidates if c.candidate_id == "blob_A")
        cand_c = next(c for c in candidates if c.candidate_id == "blob_C")
        assert cand_a.params["area_min"] > cand_c.params["area_min"]

    def test_overlay_image_path_is_str_or_none(self, engine, ok_images, ng_images):
        """overlay_image_path must be a str path or None (graceful failure allowed)."""
        for c in engine.run(ok_images, ng_images):
            assert c.overlay_image_path is None or isinstance(
                c.overlay_image_path, str
            )
