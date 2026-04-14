"""
Tests for LinearCaliperInspectionEngine (Step 36).

All images are synthesised in-memory — no external files required.
Minimum 16 pytest test functions as specified.
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from core.inspection.circular_caliper_inspector import (
    CaliperCondition,
    CaliperPolarity,
)
from core.inspection.linear_caliper_inspector import (
    LinearCaliperDirection,
    LinearCaliperInspectionEngine,
    LinearCaliperPreset,
    _compute_measurements,
    _draw_overlay,
    _reject_linear_outliers,
)
from core.models import InspectionCandidate


# ─── Synthetic image helpers ──────────────────────────────────────────────────

def _rect_image(
    h: int = 200,
    w: int = 300,
    rect_x: int = 50,
    rect_y: int = 50,
    rect_w: int = 200,
    rect_h: int = 100,
) -> np.ndarray:
    """Black background with a filled white rectangle (grayscale)."""
    img = np.zeros((h, w), dtype=np.uint8)
    img[rect_y: rect_y + rect_h, rect_x: rect_x + rect_w] = 200
    return img


def _rect_image_bgr(
    h: int = 200,
    w: int = 300,
    rect_x: int = 50,
    rect_y: int = 50,
    rect_w: int = 200,
    rect_h: int = 100,
) -> np.ndarray:
    """BGR version of the rectangle image."""
    gray = _rect_image(h, w, rect_x, rect_y, rect_w, rect_h)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _default_engine() -> LinearCaliperInspectionEngine:
    """Return a default engine with no parameter overrides."""
    return LinearCaliperInspectionEngine()


def _default_preset(
    caliper_count: int = 8,
    direction: LinearCaliperDirection = LinearCaliperDirection.RIGHTWARD,
    condition: CaliperCondition = CaliperCondition.BEST,
) -> LinearCaliperPreset:
    """Return a standard preset for direct unit testing."""
    return LinearCaliperPreset(
        caliper_count=caliper_count,
        direction=direction,
        condition=condition,
        polarity=CaliperPolarity.BRIGHTER,
        search_length=60,
        projection_length=10,
        threshold_factor=0.5,  # relaxed for synthetic test images
    )


# ─── Test classes ─────────────────────────────────────────────────────────────

class TestEngineInstantiation:

    def test_instantiation_no_params(self):
        """Engine must be instantiable with no arguments."""
        engine = LinearCaliperInspectionEngine()
        assert engine is not None

    def test_instantiation_with_params(self):
        """Engine must accept an optional params dict."""
        engine = LinearCaliperInspectionEngine(params={"caliper_count": 10})
        assert engine is not None

    def test_get_strategy_name(self):
        """get_strategy_name() must return 'LinearCaliper'."""
        assert _default_engine().get_strategy_name() == "LinearCaliper"


class TestRunBasic:

    def test_run_returns_list_on_valid_input(self):
        """run() must return a non-empty list on a valid rectangle image."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_returns_three_candidates(self):
        """run() must return exactly 3 InspectionCandidate objects."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok)
        assert len(results) == 3

    def test_candidates_are_inspection_candidate_instances(self):
        """Every result must be an InspectionCandidate."""
        engine = _default_engine()
        ok = [_rect_image()]
        for c in engine.run(ok_images=ok):
            assert isinstance(c, InspectionCandidate)

    def test_best_candidate_not_none(self):
        """The top-ranked candidate (results[0]) must not be None."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok)
        assert results[0] is not None

    def test_raises_on_empty_ok_images(self):
        """run() must raise ValueError when ok_images is empty."""
        engine = _default_engine()
        with pytest.raises(ValueError):
            engine.run(ok_images=[])

    def test_no_ng_images_completes(self):
        """run() without NG images must complete and return 3 candidates."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok, ng_images=None)
        assert len(results) == 3

    def test_roi_none_uses_full_image(self):
        """Passing roi=None must use the full image dimensions."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok, roi=None)
        assert len(results) >= 1


class TestMeasurements:

    def test_width_is_positive_float(self):
        """mean_width in _compute_measurements must be a positive float."""
        gray = _rect_image()
        preset = _default_preset()
        m = _compute_measurements(gray, preset)
        assert isinstance(m["mean_width"], float)
        assert m["mean_width"] > 0.0

    def test_straightness_is_nonnegative(self):
        """straightness metric must be >= 0."""
        gray = _rect_image()
        preset = _default_preset()
        m = _compute_measurements(gray, preset)
        assert m["straightness"] >= 0.0

    def test_parallelism_is_nonnegative(self):
        """parallelism metric must be >= 0."""
        gray = _rect_image()
        preset = _default_preset()
        m = _compute_measurements(gray, preset)
        assert m["parallelism"] >= 0.0

    def test_valid_count_does_not_exceed_caliper_count(self):
        """valid_count must not exceed the total caliper_count."""
        gray = _rect_image()
        preset = _default_preset(caliper_count=8)
        m = _compute_measurements(gray, preset)
        assert m["valid_count"] <= preset.caliper_count


class TestOutlierRemoval:

    def test_outlier_removal_excludes_far_value(self):
        """
        A value that is far (> 3σ) from the mean must be marked as outlier
        by _reject_linear_outliers.

        Mathematical note: a single outlier among N inliers is rejected only
        when sqrt(N) > 3, i.e. N >= 10.  We use 20 inliers so rejection is
        guaranteed regardless of the outlier magnitude.
        """
        # 20 tightly-clustered inliers + 1 extreme outlier
        values = [100.0] * 20 + [10000.0]
        mask = _reject_linear_outliers(values)
        # The outlier (last index) must be marked False
        assert mask[-1] is False, (
            f"Expected outlier at last index to be rejected; mask={mask}"
        )

    def test_outlier_removal_keeps_inliers(self):
        """Inliers within 3σ must all be kept."""
        values = [100.0, 101.0, 99.0, 102.0, 98.0]
        mask = _reject_linear_outliers(values)
        assert all(mask), f"All inliers should be kept; mask={mask}"


class TestValidityCheck:

    def test_low_valid_count_triggers_warning(self):
        """
        When valid_caliper_count < 4, the design_doc['warnings'] of a candidate
        must contain the phrase '유효 Caliper 수 부족'.
        """
        # Tiny image: calipers will have almost nothing to detect
        tiny = np.zeros((20, 20), dtype=np.uint8)
        engine = _default_engine()
        results = engine.run(ok_images=[tiny])
        # Find any candidate with low valid_count and check its warning
        found_warning = False
        for c in results:
            ws = c.design_doc.get("warnings", [])
            if any("유효 Caliper 수 부족" in w for w in ws):
                found_warning = True
                break
        assert found_warning, "Expected low-count warning in at least one candidate"


class TestOverlay:

    def test_overlay_is_bgr_ndarray(self):
        """_draw_overlay must return a BGR (3-channel) numpy ndarray."""
        gray = _rect_image()
        preset = _default_preset()
        m = _compute_measurements(gray, preset)
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        overlay = _draw_overlay(bgr, m, preset.direction)
        assert isinstance(overlay, np.ndarray)
        assert overlay.ndim == 3
        assert overlay.shape[2] == 3

    def test_overlay_shape_matches_source(self):
        """Overlay shape (H, W) must match the source image."""
        src = _rect_image_bgr(200, 300)
        gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        preset = _default_preset()
        m = _compute_measurements(gray, preset)
        overlay = _draw_overlay(src, m, preset.direction)
        assert overlay.shape[:2] == src.shape[:2]

    def test_overlay_via_engine_method(self):
        """Engine._draw_overlay must also return the correct BGR ndarray."""
        engine = _default_engine()
        gray = _rect_image()
        preset = _default_preset()
        m = _compute_measurements(gray, preset)
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        overlay = engine._draw_overlay(bgr, m, preset.direction)
        assert overlay.ndim == 3 and overlay.shape[2] == 3


class TestDesignDoc:

    def test_design_doc_has_four_sections(self):
        """design_doc must contain keys: placement, caliper_params, result_calculation, rationale."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok)
        required_keys = {"placement", "caliper_params", "result_calculation", "rationale"}
        for c in results:
            missing = required_keys - c.design_doc.keys()
            assert not missing, f"Missing design_doc keys: {missing}"

    def test_library_mapping_has_four_vendors(self):
        """
        design_doc['library_mapping']['concept_table'] entries must contain
        Keyence, Cognex, Halcon, and MIL keys.
        """
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok)
        for c in results:
            table = c.design_doc["library_mapping"]["concept_table"]
            for concept, entries in table.items():
                for vendor in ("Keyence", "Cognex", "Halcon", "MIL"):
                    assert vendor in entries, (
                        f"Vendor '{vendor}' missing in concept '{concept}'"
                    )

    def test_design_doc_is_json_serialisable(self):
        """design_doc must be fully JSON-serialisable."""
        engine = _default_engine()
        ok = [_rect_image()]
        results = engine.run(ok_images=ok)
        for c in results:
            dumped = json.dumps(c.design_doc)
            assert isinstance(dumped, str)


class TestLinearCaliperDirectionEnum:

    def test_direction_enum_values(self):
        """LinearCaliperDirection must expose LEFTWARD, RIGHTWARD, UPWARD, DOWNWARD."""
        assert LinearCaliperDirection.LEFTWARD.value  == "Leftward"
        assert LinearCaliperDirection.RIGHTWARD.value == "Rightward"
        assert LinearCaliperDirection.UPWARD.value    == "Upward"
        assert LinearCaliperDirection.DOWNWARD.value  == "Downward"

    def test_direction_enum_all_members_present(self):
        """All four direction members must be accessible."""
        members = {d.name for d in LinearCaliperDirection}
        for name in ("LEFTWARD", "RIGHTWARD", "UPWARD", "DOWNWARD"):
            assert name in members, f"Missing LinearCaliperDirection.{name}"
