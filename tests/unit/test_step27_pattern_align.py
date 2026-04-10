"""
Step 27 — Unit tests for PatternAlignEngine (TM_CCOEFF_NORMED).

All test images are synthesised with numpy; no external files are required.
"""

import numpy as np
import pytest

from core.align.pattern_align import PatternAlignEngine, PatternAlignResult
from core.models import ROIConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_textured(size: int = 30) -> np.ndarray:
    """Return a deterministic 5-px checkerboard pattern (grayscale uint8)."""
    img = np.zeros((size, size), dtype=np.uint8)
    for r in range(size):
        for c in range(size):
            if (r // 5 + c // 5) % 2 == 0:
                img[r, c] = 220
    return img


def _embed(template: np.ndarray, canvas_h: int, canvas_w: int, y: int, x: int) -> np.ndarray:
    """Place *template* at (x, y) inside a zero-filled canvas and return it."""
    canvas = np.zeros((canvas_h, canvas_w), dtype=np.uint8)
    th, tw = template.shape[:2]
    canvas[y : y + th, x : x + tw] = template
    return canvas


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPatternAlignEngine:

    def test_pattern_align_engine_instantiation(self):
        """PatternAlignEngine() must construct without raising any exception."""
        engine = PatternAlignEngine()
        assert engine is not None
        assert engine.get_strategy_name() == "Pattern Matching"

    def test_align_identical_images_returns_success(self):
        """Template cropped from the image centre must match with score near 1.0."""
        template = _make_textured(40)
        image = _embed(template, canvas_h=120, canvas_w=120, y=40, x=40)

        engine = PatternAlignEngine(threshold=0.6)
        result = engine.align(image, template)

        assert isinstance(result, PatternAlignResult)
        assert result.success is True
        assert result.score >= 0.95

    def test_align_offset_image_returns_correct_offset(self):
        """Template embedded at (50, 70) must be recovered with ≤ 2 px error."""
        expected_x, expected_y = 50, 70
        template = _make_textured(30)
        image = _embed(template, canvas_h=200, canvas_w=200, y=expected_y, x=expected_x)

        engine = PatternAlignEngine(threshold=0.5)
        result = engine.align(image, template)

        assert result.success is True
        assert abs(result.offset_x - expected_x) <= 2
        assert abs(result.offset_y - expected_y) <= 2

    def test_align_unrelated_images_returns_failure(self):
        """Random-noise image vs textured template must yield success=False.

        A constant template has zero variance and produces score=1.0 everywhere
        (TM_CCOEFF_NORMED edge-case), so we use a textured checkerboard template
        against pure random noise, which should score well below 0.85.
        """
        rng = np.random.default_rng(seed=42)
        image = rng.integers(0, 256, (100, 100), dtype=np.uint8)

        # Textured checkerboard: non-trivially correlated with structured signal
        template = _make_textured(20)

        engine = PatternAlignEngine(threshold=0.85)   # tight threshold
        result = engine.align(image, template)

        assert result.success is False

    def test_align_none_image_returns_failure(self):
        """Passing image=None must return AlignResult with success=False."""
        engine = PatternAlignEngine()
        result = engine.align(None, np.zeros((10, 10), dtype=np.uint8))

        assert result.success is False
        assert result.error_message is not None

    def test_align_template_larger_than_image_returns_failure(self):
        """Template (50×50) larger than image (30×30) must return success=False."""
        image = np.zeros((30, 30), dtype=np.uint8)
        template = np.ones((50, 50), dtype=np.uint8) * 200

        engine = PatternAlignEngine()
        result = engine.align(image, template)

        assert result.success is False
        assert result.error_message is not None

    def test_align_with_roi_config_applies_crop(self):
        """Offset must be expressed in full-image coordinates when ROI is active."""
        template = _make_textured(30)
        # Embed pattern at (80, 80) in a 200×200 canvas
        image = _embed(template, canvas_h=200, canvas_w=200, y=80, x=80)

        # ROI that covers the pattern region
        roi = ROIConfig(x=60, y=60, width=100, height=100)

        engine = PatternAlignEngine(threshold=0.5)
        result = engine.align(image, template, roi=roi)

        assert result.success is True
        # Offset must be in full-image coordinates (≈80, 80)
        assert abs(result.offset_x - 80) <= 2
        assert abs(result.offset_y - 80) <= 2

    def test_generate_design_doc_contains_sections(self):
        """generate_design_doc() must include all four required section headers."""
        engine = PatternAlignEngine(threshold=0.6)
        dummy = PatternAlignResult(
            success=True,
            strategy_name="Pattern Matching",
            score=0.92,
            offset_x=10.0,
            offset_y=5.0,
        )
        doc = engine.generate_design_doc(dummy, template_size=(30, 30), search_size=(100, 100))

        assert "[Section 1: 배치 구조]" in doc
        assert "[Section 2: 매칭 파라미터]" in doc
        assert "[Section 3: 결과 계산 방식]" in doc
        assert "[Section 4: 선택 근거]" in doc

    def test_align_result_has_design_doc(self):
        """A successful align() call must store a non-empty design_doc string."""
        template = _make_textured(30)
        image = _embed(template, canvas_h=120, canvas_w=120, y=45, x=45)

        engine = PatternAlignEngine(threshold=0.5)
        result = engine.align(image, template)

        assert result.success is True
        assert isinstance(result.design_doc, str)
        assert len(result.design_doc) > 0

    def test_align_bgr_image_converted_to_gray(self):
        """BGR 3-channel input must be handled without error (auto grayscale)."""
        template_gray = _make_textured(30)
        image_gray = _embed(template_gray, 120, 120, 40, 40)

        # Wrap as BGR
        image_bgr = np.stack([image_gray, image_gray, image_gray], axis=-1)
        template_bgr = np.stack([template_gray, template_gray, template_gray], axis=-1)

        engine = PatternAlignEngine(threshold=0.5)
        result = engine.align(image_bgr, template_bgr)

        assert result.success is True

    def test_run_delegates_to_align(self):
        """IAlignEngine.run() must return a valid PatternAlignResult."""
        template = _make_textured(30)
        image = _embed(template, 120, 120, 45, 45)

        engine = PatternAlignEngine(threshold=0.5)
        result = engine.run(image, template)

        assert isinstance(result, PatternAlignResult)
        assert result.success is True
        assert result.strategy_name == "Pattern Matching"
