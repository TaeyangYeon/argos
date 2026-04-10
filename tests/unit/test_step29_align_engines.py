"""
Step 29 — Feature / Contour / Blob Align 엔진 유닛 테스트

Synthetic images are generated with NumPy / OpenCV — no external files required.
All 15 tests must pass with:
    pytest tests/unit/test_step29_align_engines.py -v
"""

from __future__ import annotations

import numpy as np
import cv2
import pytest

from core.align.feature_align import FeatureAlignEngine
from core.align.contour_align import ContourAlignEngine
from core.align.blob_align import BlobAlignEngine
from core.models import AlignResult, ROIConfig


# ─── Synthetic image helpers ─────────────────────────────────────────────────

def make_checkerboard(size: int = 200, block: int = 20) -> np.ndarray:
    """Rich-texture checkerboard; many ORB keypoints expected."""
    gray = np.zeros((size, size), dtype=np.uint8)
    for r in range(0, size, block):
        for c in range(0, size, block):
            if (r // block + c // block) % 2 == 0:
                gray[r : r + block, c : c + block] = 255
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def make_blank(size: int = 200) -> np.ndarray:
    """Uniform black image — no features, no edges, no blobs."""
    return np.zeros((size, size, 3), dtype=np.uint8)


def make_rectangle_image(size: int = 200) -> np.ndarray:
    """Filled white rectangle on black — clear contour present."""
    gray = np.zeros((size, size), dtype=np.uint8)
    cv2.rectangle(gray, (40, 40), (160, 160), 255, -1)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def make_circle_image(size: int = 200) -> np.ndarray:
    """Filled white circle on black — bright blob; engine inverts internally."""
    gray = np.zeros((size, size), dtype=np.uint8)
    cv2.circle(gray, (100, 100), 40, 255, -1)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


# ─── Feature Align ────────────────────────────────────────────────────────────

class TestFeatureAlignEngine:

    def test_feature_align_engine_instantiation(self):
        engine = FeatureAlignEngine()
        assert engine is not None
        assert engine.get_strategy_name() == "Feature Matching"

    def test_feature_align_returns_align_result(self):
        engine = FeatureAlignEngine()
        img = make_checkerboard()
        result = engine.run(img, img)
        assert isinstance(result, AlignResult)

    def test_feature_align_with_identical_images_succeeds(self):
        engine = FeatureAlignEngine()
        img = make_checkerboard()
        result = engine.run(img, img)
        assert result.success is True
        assert result.score > 0.0

    def test_feature_align_design_doc_has_four_sections(self):
        engine = FeatureAlignEngine()
        img = make_checkerboard()
        result = engine.run(img, img)
        assert hasattr(result, "design_doc")
        doc = result.design_doc
        assert isinstance(doc, dict)
        assert "placement" in doc
        assert "parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc

    def test_feature_align_insufficient_matches_fails(self):
        engine = FeatureAlignEngine(min_matches=8)
        blank = make_blank()
        result = engine.run(blank, blank)
        assert result.success is False


# ─── Contour Align ───────────────────────────────────────────────────────────

class TestContourAlignEngine:

    def test_contour_align_engine_instantiation(self):
        engine = ContourAlignEngine()
        assert engine is not None
        assert engine.get_strategy_name() == "Contour Matching"

    def test_contour_align_returns_align_result(self):
        engine = ContourAlignEngine()
        ref = make_rectangle_image()
        result = engine.run(ref, ref)
        assert isinstance(result, AlignResult)

    def test_contour_align_with_clear_shape_succeeds(self):
        engine = ContourAlignEngine()
        ref = make_rectangle_image()
        result = engine.run(ref, ref)
        assert result.success is True
        assert result.score > 0.0

    def test_contour_align_design_doc_has_four_sections(self):
        engine = ContourAlignEngine()
        ref = make_rectangle_image()
        result = engine.run(ref, ref)
        assert hasattr(result, "design_doc")
        doc = result.design_doc
        assert isinstance(doc, dict)
        assert "placement" in doc
        assert "parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc

    def test_contour_align_blank_image_fails(self):
        engine = ContourAlignEngine()
        blank = make_blank()
        result = engine.run(blank, blank)
        assert result.success is False


# ─── Blob Align ───────────────────────────────────────────────────────────────

class TestBlobAlignEngine:

    def test_blob_align_engine_instantiation(self):
        engine = BlobAlignEngine()
        assert engine is not None
        assert engine.get_strategy_name() == "Blob Matching"

    def test_blob_align_returns_align_result(self):
        engine = BlobAlignEngine()
        ref = make_circle_image()
        result = engine.run(ref, ref)
        assert isinstance(result, AlignResult)

    def test_blob_align_with_visible_blob_succeeds(self):
        engine = BlobAlignEngine()
        ref = make_circle_image()
        result = engine.run(ref, ref)
        assert result.success is True
        assert result.score == 1.0

    def test_blob_align_design_doc_has_four_sections(self):
        engine = BlobAlignEngine()
        ref = make_circle_image()
        result = engine.run(ref, ref)
        assert hasattr(result, "design_doc")
        doc = result.design_doc
        assert isinstance(doc, dict)
        assert "placement" in doc
        assert "parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc

    def test_blob_align_no_blob_fails(self):
        engine = BlobAlignEngine()
        blank = make_blank()
        result = engine.run(blank, blank)
        assert result.success is False
