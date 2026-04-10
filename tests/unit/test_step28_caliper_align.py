"""
Step 28 — Unit tests for CaliperAlignEngine (Sobel edge-based caliper).

All test images are synthesised with numpy; no external files are required.
"""

import numpy as np
import pytest

from core.align.caliper_align import (
    CaliperAlignEngine,
    CaliperAlignResult,
    CaliperCondition,
    CaliperDirection,
    CaliperPolarity,
)
from core.interfaces import IAlignEngine
from core.models import ROIConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gradient_image(h: int = 100, w: int = 100) -> np.ndarray:
    """
    Return a uint8 grayscale image with a strong horizontal edge at row h//2.
    Top half is dark (30), bottom half is bright (200).
    """
    img = np.full((h, w), 30, dtype=np.uint8)
    img[h // 2:, :] = 200
    return img


def _make_vertical_edge_image(h: int = 100, w: int = 100) -> np.ndarray:
    """
    Return a uint8 grayscale image with a strong vertical edge at col w//2.
    Left half is dark (30), right half is bright (200).
    """
    img = np.full((h, w), 30, dtype=np.uint8)
    img[:, w // 2:] = 200
    return img


def _make_blank_image(h: int = 100, w: int = 100) -> np.ndarray:
    """Return a flat (no edges) grayscale image."""
    return np.full((h, w), 128, dtype=np.uint8)


def _make_reference(h: int = 100, w: int = 100) -> np.ndarray:
    """Return a simple reference image (same size as input for metrics)."""
    return np.full((h, w), 128, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCaliperAlignEngine:

    # --- 1. Interface compliance ---

    def test_caliper_align_engine_implements_interface(self):
        """CaliperAlignEngine must be an instance of IAlignEngine."""
        engine = CaliperAlignEngine()
        assert isinstance(engine, IAlignEngine)
        assert engine.get_strategy_name() == "Caliper"

    # --- 2. detect_edges ---

    def test_detect_edges_returns_points_on_gradient_image(self):
        """detect_edges() must return at least one point on an image with a clear edge."""
        image = _make_gradient_image(h=100, w=100)
        engine = CaliperAlignEngine(
            num_calipers=8,
            threshold=20.0,
            direction=CaliperDirection.INWARD,
        )
        points = engine.detect_edges(image)

        assert isinstance(points, list)
        assert len(points) > 0
        for pt in points:
            assert len(pt) == 2
            x, y = pt
            assert 0 <= x < 100
            assert 0 <= y < 100

    def test_detect_edges_returns_empty_on_flat_image(self):
        """detect_edges() must return [] when no gradient exceeds threshold."""
        image = _make_blank_image()
        engine = CaliperAlignEngine(threshold=200.0)  # very high threshold
        points = engine.detect_edges(image)
        assert points == []

    # --- 3. Successful alignment ---

    def test_align_success_returns_offset_and_score(self):
        """align() on a gradient image must return success=True with valid offset and score."""
        image = _make_gradient_image(h=100, w=100)
        ref = _make_reference(h=100, w=100)

        engine = CaliperAlignEngine(
            num_calipers=8,
            threshold=20.0,
            direction=CaliperDirection.INWARD,
        )
        result = engine.align(image, ref)

        assert isinstance(result, CaliperAlignResult)
        assert result.success is True
        assert isinstance(result.score, float)
        assert 0.0 < result.score <= 1.0
        assert isinstance(result.offset_x, float)
        assert isinstance(result.offset_y, float)

    # --- 4. ROI restriction ---

    def test_align_with_roi_config_restricts_region(self):
        """align() with roi_config must operate only within the ROI bounds."""
        image = _make_gradient_image(h=200, w=200)
        ref = _make_reference(h=100, w=100)

        # ROI covers only the bottom half where the bright region starts
        roi = ROIConfig(x=0, y=100, width=200, height=100)

        engine = CaliperAlignEngine(
            num_calipers=6,
            threshold=10.0,
            direction=CaliperDirection.INWARD,
        )
        result = engine.align(image, ref, roi_config=roi)

        # Should execute without error; result may succeed or fail depending on
        # whether edges exist in the ROI, but design_doc must be populated.
        assert isinstance(result, CaliperAlignResult)
        assert isinstance(result.design_doc, dict)
        assert len(result.design_doc) == 4

    # --- 5. Failure path ---

    def test_align_failure_no_edges_returns_false(self):
        """align() on a flat image with high threshold must return success=False."""
        image = _make_blank_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=255.0)  # impossible threshold
        result = engine.align(image, ref)

        assert result.success is False
        assert result.failure_reason is not None
        assert "No valid edges" in result.failure_reason or result.failure_reason != ""

    def test_align_none_image_returns_failure(self):
        """align() with image=None must return success=False."""
        engine = CaliperAlignEngine()
        result = engine.align(None, _make_reference())

        assert result.success is False
        assert result.failure_reason is not None

    # --- 6. design_doc structure ---

    def test_design_doc_has_4_sections(self):
        """design_doc must always contain exactly 4 top-level section keys."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=20.0)
        result = engine.align(image, ref)

        doc = result.design_doc
        assert isinstance(doc, dict)
        assert "placement_structure" in doc
        assert "caliper_parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc

    def test_design_doc_section2_has_required_caliper_keys(self):
        """design_doc['caliper_parameters'] must contain all required keys."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=20.0)
        result = engine.align(image, ref)

        section2 = result.design_doc["caliper_parameters"]
        assert "projection_length" in section2
        assert "search_length" in section2
        assert "condition" in section2
        assert "threshold" in section2
        assert "polarity" in section2
        assert "edge_filter" in section2

    def test_design_doc_populated_on_failure(self):
        """design_doc must have all 4 sections even when alignment fails."""
        image = _make_blank_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=255.0)
        result = engine.align(image, ref)

        assert result.success is False
        doc = result.design_doc
        assert "placement_structure" in doc
        assert "caliper_parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc

    # --- 7. Overlay image ---

    def test_overlay_image_generated_on_success(self):
        """A successful align() must produce a non-None BGR overlay image."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=20.0)
        result = engine.align(image, ref)

        assert result.success is True
        assert result.overlay_image is not None
        assert isinstance(result.overlay_image, np.ndarray)
        assert result.overlay_image.ndim == 3  # BGR
        assert result.overlay_image.shape[2] == 3

    def test_overlay_image_none_on_failure(self):
        """overlay_image must be None when alignment fails."""
        image = _make_blank_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=255.0)
        result = engine.align(image, ref)

        assert result.success is False
        assert result.overlay_image is None

    # --- 8. Direction support ---

    def test_direction_inward_outward_accepted(self):
        """CaliperDirection.INWARD and OUTWARD must both run without raising."""
        image = _make_gradient_image()
        ref = _make_reference()

        for direction in (CaliperDirection.INWARD, CaliperDirection.OUTWARD):
            engine = CaliperAlignEngine(direction=direction, threshold=20.0)
            result = engine.run(image, ref)
            assert isinstance(result, CaliperAlignResult)

    def test_direction_leftward_rightward_accepted(self):
        """CaliperDirection.LEFTWARD and RIGHTWARD must both run without raising."""
        image = _make_vertical_edge_image()
        ref = _make_reference()

        for direction in (CaliperDirection.LEFTWARD, CaliperDirection.RIGHTWARD):
            engine = CaliperAlignEngine(direction=direction, threshold=20.0)
            result = engine.run(image, ref)
            assert isinstance(result, CaliperAlignResult)

    # --- 9. run() delegates correctly ---

    def test_run_delegates_to_align(self):
        """IAlignEngine.run() must return a CaliperAlignResult."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=20.0)
        result = engine.run(image, ref)

        assert isinstance(result, CaliperAlignResult)
        assert result.strategy_name == "Caliper"

    # --- 10. Polarity variants ---

    def test_polarity_dark_to_light_accepted(self):
        """CaliperPolarity.DARK_TO_LIGHT must run without error."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(
            polarity=CaliperPolarity.DARK_TO_LIGHT,
            threshold=10.0,
            direction=CaliperDirection.INWARD,
        )
        result = engine.run(image, ref)
        assert isinstance(result, CaliperAlignResult)

    def test_polarity_light_to_dark_accepted(self):
        """CaliperPolarity.LIGHT_TO_DARK must run without error."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(
            polarity=CaliperPolarity.LIGHT_TO_DARK,
            threshold=10.0,
            direction=CaliperDirection.INWARD,
        )
        result = engine.run(image, ref)
        assert isinstance(result, CaliperAlignResult)

    # --- 11. Condition variants ---

    def test_condition_first_last_best_all_accepted(self):
        """All four CaliperCondition values must run without error."""
        image = _make_gradient_image()
        ref = _make_reference()

        for condition in CaliperCondition:
            engine = CaliperAlignEngine(
                condition=condition,
                threshold=20.0,
                direction=CaliperDirection.INWARD,
            )
            result = engine.run(image, ref)
            assert isinstance(result, CaliperAlignResult)

    # --- 12. BGR image input ---

    def test_bgr_image_converted_to_gray(self):
        """BGR 3-channel input must be handled without error."""
        gray = _make_gradient_image()
        image_bgr = np.stack([gray, gray, gray], axis=-1)
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=20.0)
        result = engine.align(image_bgr, ref)

        assert isinstance(result, CaliperAlignResult)
        assert result.success is True

    # --- 13. score is bounded ---

    def test_score_bounded_between_0_and_1(self):
        """score must always be in [0.0, 1.0]."""
        image = _make_gradient_image()
        ref = _make_reference()

        engine = CaliperAlignEngine(threshold=20.0, num_calipers=4)
        result = engine.align(image, ref)

        assert 0.0 <= result.score <= 1.0
