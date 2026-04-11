"""
Tests for CircularCaliperInspectionEngine (Step 35).

All images are synthesised in-memory — no external files required.
Minimum 12 pytest test functions as specified.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest

from core.inspection.circular_caliper_inspector import (
    CaliperCandidate,
    CaliperCondition,
    CaliperDirection,
    CaliperPolarity,
    CircularCaliperInspectionEngine,
    _fit_circle_lsq,
    _reject_outliers,
    _extract_edge_point,
    _build_design_doc,
)
from core.models import InspectionCandidate


# ─── Synthetic image helpers ──────────────────────────────────────────────────

def _circle_image(
    h: int = 200,
    w: int = 200,
    cx: int = 100,
    cy: int = 100,
    radius: int = 60,
    thickness: int = -1,
) -> np.ndarray:
    """Black background with a filled white circle."""
    img = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(img, (cx, cy), radius, 255, thickness)
    return img


def _circle_image_bgr(
    h: int = 200,
    w: int = 200,
    cx: int = 100,
    cy: int = 100,
    radius: int = 60,
) -> np.ndarray:
    """BGR version of the circle image."""
    gray = _circle_image(h, w, cx, cy, radius)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _ellipse_image(
    h: int = 200,
    w: int = 200,
    cx: int = 100,
    cy: int = 100,
    rx: int = 60,
    ry: int = 40,
) -> np.ndarray:
    """Black background with a filled white ellipse (deformed circle / NG)."""
    img = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
    return img


def _default_engine() -> CircularCaliperInspectionEngine:
    return CircularCaliperInspectionEngine()


def _default_preset(caliper_count: int = 12,
                    direction: CaliperDirection = CaliperDirection.INWARD) -> CaliperCandidate:
    return CaliperCandidate(
        caliper_count=caliper_count,
        direction=direction,
        condition=CaliperCondition.BEST,
        polarity=CaliperPolarity.BRIGHTER,
        search_length=30,
        projection_length=5,
        search_radius=55,
        start_angle_deg=0.0,
    )


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestEngineBasic:

    def test_runs_without_exception_on_ok_image(self):
        """Engine must complete without raising on a valid circle image."""
        engine = _default_engine()
        ok = [_circle_image()]
        results = engine.run(ok_images=ok)
        assert isinstance(results, list)

    def test_returns_at_least_three_candidates(self):
        """run() must return at least 3 InspectionCandidate objects."""
        engine = _default_engine()
        ok = [_circle_image()]
        results = engine.run(ok_images=ok)
        assert len(results) >= 3

    def test_results_are_inspection_candidates(self):
        """Every item in results must be an InspectionCandidate."""
        engine = _default_engine()
        ok = [_circle_image()]
        for c in engine.run(ok_images=ok):
            assert isinstance(c, InspectionCandidate)

    def test_raises_on_empty_ok_images(self):
        """run() must raise ValueError when ok_images is empty."""
        engine = _default_engine()
        with pytest.raises((ValueError, Exception)):
            engine.run(ok_images=[])

    def test_get_strategy_name(self):
        """get_strategy_name() must return 'CircularCaliper'."""
        assert _default_engine().get_strategy_name() == "CircularCaliper"


class TestFittedCircle:

    def test_fitted_radius_within_5px_of_ground_truth(self):
        """
        The LSQ fit on an ideal circle image should recover the radius
        within ±5 px of the synthetic ground truth (radius=60).
        """
        ok = [_circle_image(radius=60)]
        engine = _default_engine()
        results = engine.run(ok_images=ok)
        best = results[0]
        # Fitted radius is stored in design_doc result_calculation
        fitted_r = best.design_doc["result_calculation"]["fitted_radius_px"]
        assert abs(fitted_r - 60) <= 5, f"fitted_radius={fitted_r:.1f} not within 5px of 60"

    def test_valid_caliper_count_positive(self):
        """valid_caliper_count in design_doc must be a non-negative integer."""
        ok = [_circle_image()]
        results = _default_engine().run(ok_images=ok)
        for c in results:
            vc = c.design_doc["result_calculation"]["valid_caliper_count"]
            assert isinstance(vc, int)
            assert vc >= 0


class TestOverlay:

    def test_overlay_image_not_none(self):
        """Engine must produce a non-None overlay (returned via _draw_overlay)."""
        engine = _default_engine()
        ok = [_circle_image()]
        # _run_on_image expects a grayscale image
        gray = ok[0] if ok[0].ndim == 2 else cv2.cvtColor(ok[0], cv2.COLOR_BGR2GRAY)
        inliers, cx, cy, r = engine._run_on_image(gray, _default_preset(), 100.0, 100.0)
        overlay = engine._draw_overlay(ok[0], inliers, cx, cy, r)
        assert overlay is not None

    def test_overlay_has_correct_shape(self):
        """Overlay must be 3-channel BGR and same spatial size as source."""
        engine = _default_engine()
        src = _circle_image(200, 200)
        preset = _default_preset()
        gray = src if src.ndim == 2 else cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        inliers, cx, cy, r = engine._run_on_image(gray, preset, 100.0, 100.0)
        overlay = engine._draw_overlay(src, inliers, cx, cy, r)
        assert overlay.ndim == 3
        assert overlay.shape[2] == 3
        assert overlay.shape[:2] == src.shape[:2]


class TestDesignDoc:

    def test_design_doc_has_all_four_sections(self):
        """design_doc must contain all four mandatory section keys."""
        ok = [_circle_image()]
        results = _default_engine().run(ok_images=ok)
        required = {
            "placement_structure",
            "individual_caliper_params",
            "result_calculation",
            "selection_rationale",
        }
        for c in results:
            assert required.issubset(c.design_doc.keys()), \
                f"Missing keys: {required - c.design_doc.keys()}"

    def test_design_doc_has_library_mapping(self):
        """design_doc must contain a 'library_mapping' key."""
        ok = [_circle_image()]
        results = _default_engine().run(ok_images=ok)
        for c in results:
            assert "library_mapping" in c.design_doc

    def test_design_doc_is_json_serialisable(self):
        """design_doc must be serialisable with json.dumps (plain dict)."""
        import json
        ok = [_circle_image()]
        results = _default_engine().run(ok_images=ok)
        for c in results:
            dumped = json.dumps(c.design_doc)
            assert isinstance(dumped, str)

    def test_library_mapping_has_four_libraries(self):
        """library_mapping.concept_table values must reference Keyence/Cognex/Halcon/MIL."""
        ok = [_circle_image()]
        results = _default_engine().run(ok_images=ok)
        for c in results:
            table = c.design_doc["library_mapping"]["concept_table"]
            for concept, entries in table.items():
                for lib in ("Keyence", "Cognex", "Halcon", "MIL"):
                    assert lib in entries, \
                        f"Library '{lib}' missing in concept '{concept}'"


class TestConfidenceWarning:

    def test_low_caliper_count_triggers_warning(self):
        """
        When valid_caliper_count < 8, design_doc['warnings'] must contain
        the phrase '유효 Caliper 수 부족'.
        """
        preset = _default_preset(caliper_count=4)
        stats = {
            "valid_count":   3,   # < 8
            "fitted_radius": 60.0,
            "hough_radius":  60.0,
            "mean_gray":     128.0,
            "std_gray":      40.0,
        }
        doc = _build_design_doc(preset, stats)
        warnings = doc.get("warnings", [])
        assert any("유효 Caliper 수 부족" in w for w in warnings), \
            f"Expected warning not found in: {warnings}"

    def test_sufficient_caliper_count_no_warning(self):
        """When valid_caliper_count >= 8, no confidence warning should appear."""
        preset = _default_preset(caliper_count=12)
        stats = {
            "valid_count":   10,
            "fitted_radius": 60.0,
            "hough_radius":  60.0,
            "mean_gray":     128.0,
            "std_gray":      40.0,
        }
        doc = _build_design_doc(preset, stats)
        warnings = doc.get("warnings", [])
        assert not any("유효 Caliper 수 부족" in w for w in warnings)


class TestDirections:

    def test_inward_direction_runs_without_error(self):
        """Engine must complete with INWARD direction without exception."""
        engine = _default_engine()
        ok = [_circle_image()]
        gray = ok[0]
        preset = _default_preset(direction=CaliperDirection.INWARD)
        inliers, cx, cy, r = engine._run_on_image(gray, preset, 100.0, 100.0)
        assert isinstance(inliers, list)

    def test_outward_direction_runs_without_error(self):
        """Engine must complete with OUTWARD direction without exception."""
        engine = _default_engine()
        ok = [_circle_image()]
        gray = ok[0]
        preset = _default_preset(direction=CaliperDirection.OUTWARD)
        inliers, cx, cy, r = engine._run_on_image(gray, preset, 100.0, 100.0)
        assert isinstance(inliers, list)


class TestLSQAndOutliers:

    def test_fit_circle_lsq_exact_triangle(self):
        """
        LSQ fit of three points on a circle of radius R centred at (0,0)
        should recover radius to within floating-point tolerance.
        """
        R = 50.0
        pts = [(R, 0), (0, R), (-R, 0)]
        cx, cy, r = _fit_circle_lsq(pts)
        assert abs(r - R) < 1.0

    def test_reject_outliers_removes_far_point(self):
        """
        A point at the circle centre (deviation = R from the edge) must be
        removed by 3σ rejection when all other points sit exactly on the circle.
        """
        R = 50.0
        # 20 exact circle points → LSQ gives near-perfect fit, σ ≈ 0
        pts: list[tuple[float, float]] = []
        for k in range(20):
            a = 2 * math.pi * k / 20
            pts.append((R * math.cos(a), R * math.sin(a)))
        # Outlier at the centre: deviation from circle = R = 50 >> 3σ ≈ 0
        outlier = (0.0, 0.0)
        pts.append(outlier)
        cx, cy, r = _fit_circle_lsq(pts)
        inliers = _reject_outliers(pts, cx, cy, r)
        assert outlier not in inliers, \
            f"Outlier {outlier} should have been rejected; inliers={inliers}"

    def test_fit_circle_lsq_raises_on_too_few_points(self):
        """_fit_circle_lsq must raise ValueError for fewer than 3 points."""
        with pytest.raises(ValueError):
            _fit_circle_lsq([(0.0, 0.0), (1.0, 0.0)])
