"""
Step 32 — Align Pipeline Integration Tests
===========================================

Scope
-----
* All five align engines tested standalone with synthetic images (no external files).
* AlignFallbackChain tested end-to-end: normal, caliper-fallback, full-fail, and AI paths.
* ROI support verified: PatternAlignEngine and CaliperAlignEngine.
* Design-document 4-section structure verified for every engine.

Total tests: 25
Run with:
    pytest tests/integration/test_align_integration.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from core.align.align_engine import AlignFallbackChain
from core.align.blob_align import BlobAlignEngine
from core.align.caliper_align import CaliperAlignEngine
from core.align.contour_align import ContourAlignEngine
from core.align.feature_align import FeatureAlignEngine
from core.align.pattern_align import PatternAlignEngine
from core.image_store import ImageStore
from core.models import AlignResult, ROIConfig


# ─── Synthetic image factory helpers ─────────────────────────────────────────

def _checkerboard(h: int = 200, w: int = 200, block: int = 20) -> np.ndarray:
    """Grayscale checkerboard: rich texture with many ORB keypoints."""
    img = np.zeros((h, w), dtype=np.uint8)
    for r in range(0, h, block):
        for c in range(0, w, block):
            if (r // block + c // block) % 2 == 0:
                img[r : r + block, c : c + block] = 200
    return img


def _high_contrast_edge(h: int = 200, w: int = 200, edge_y: int = 100) -> np.ndarray:
    """Grayscale image with a sharp horizontal edge at *edge_y*."""
    img = np.zeros((h, w), dtype=np.uint8)
    img[edge_y:, :] = 200
    return img


def _circle_image(
    h: int = 200, w: int = 200, cx: int = 100, cy: int = 100, r: int = 40
) -> np.ndarray:
    """White filled circle on black background — clear blob and contour."""
    img = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(img, (cx, cy), r, 255, -1)
    return img


def _rectangle_image(h: int = 200, w: int = 200) -> np.ndarray:
    """White filled rectangle on black background — clear contour."""
    img = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (160, 160), 255, -1)
    return img


# ─── Chain test helpers ───────────────────────────────────────────────────────

def _ok_result(strategy: str = "mock", score: float = 0.9) -> AlignResult:
    return AlignResult(success=True, strategy_name=strategy, score=score)


def _fail_result(strategy: str = "mock", reason: str = "mocked failure") -> AlignResult:
    return AlignResult(
        success=False, strategy_name=strategy, score=0.0, failure_reason=reason
    )


def _make_chain(ai_provider=None) -> AlignFallbackChain:
    store = MagicMock(spec=ImageStore)
    store.get_all.return_value = []   # no reference images → zero-image fallback
    return AlignFallbackChain(
        image_store=store,
        roi_config=None,
        ai_provider=ai_provider,
    )


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def pattern_image_and_template() -> tuple[np.ndarray, np.ndarray]:
    """300×300 image containing a 60×60 checkerboard template at position (100, 80)."""
    template = _checkerboard(60, 60, block=10)
    image = np.zeros((300, 300), dtype=np.uint8)
    image[80:140, 100:160] = template          # rows 80–139, cols 100–159
    return image, template


@pytest.fixture(scope="function")
def high_contrast_image() -> np.ndarray:
    """200×200 grayscale with a sharp horizontal edge at y = 100."""
    return _high_contrast_edge(200, 200, 100)


@pytest.fixture(scope="function")
def checkerboard_pair() -> tuple[np.ndarray, np.ndarray]:
    """A rich-texture reference and the same image (0-shift) for feature matching."""
    ref = _checkerboard(200, 200, 20)
    return ref, ref.copy()


@pytest.fixture(scope="function")
def rectangle_images() -> tuple[np.ndarray, np.ndarray]:
    """Two identical rectangle images for contour matching (matchShapes ≈ 0)."""
    img = _rectangle_image()
    return img.copy(), img.copy()


@pytest.fixture(scope="function")
def blob_images() -> tuple[np.ndarray, np.ndarray]:
    """Reference blob centred at (100, 100); image blob shifted to (110, 105)."""
    ref = _circle_image(cx=100, cy=100)
    img = _circle_image(cx=110, cy=105)
    return ref, img


@pytest.fixture(scope="function")
def dummy_reference() -> np.ndarray:
    """100×100 mid-grey image used as a placeholder reference in chain tests."""
    return np.full((100, 100), 128, dtype=np.uint8)


# ═══════════════════════════════════════════════════════════════════════════════
# TestPatternAlignEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestPatternAlignEngine:
    """Standalone integration tests for PatternAlignEngine (TM_CCOEFF_NORMED)."""

    def test_valid_template_match_known_offset(self, pattern_image_and_template):
        """PatternAlignEngine locates template and reports the correct offset.

        The template (60×60 checkerboard) is embedded at column 100, row 80 in
        a 300×300 search image.  TM_CCOEFF_NORMED should return score = 1.0 and
        offset_x ≈ 100, offset_y ≈ 80.
        """
        # Arrange
        image, template = pattern_image_and_template
        engine = PatternAlignEngine(threshold=0.5)

        # Act
        result = engine.align(image, template)

        # Assert
        assert result.success, f"Expected success; got: {result.failure_reason}"
        assert result.score >= 0.5
        assert abs(result.offset_x - 100.0) < 5.0, f"offset_x={result.offset_x}"
        assert abs(result.offset_y - 80.0) < 5.0, f"offset_y={result.offset_y}"

    def test_align_fails_when_template_absent_from_image(self):
        """Score below threshold when template is absent → failure with reason."""
        # Arrange: a blank image cannot produce a high correlation with a checkerboard
        image = np.zeros((200, 200), dtype=np.uint8)
        template = _checkerboard(60, 60, block=10)
        engine = PatternAlignEngine(threshold=0.9)

        # Act
        result = engine.align(image, template)

        # Assert
        assert not result.success
        assert result.score < 0.9
        assert result.failure_reason is not None

    def test_roi_containing_template_succeeds_with_full_image_coords(
        self, pattern_image_and_template
    ):
        """With an ROI that contains the template, offset is reported in full-image frame."""
        # Arrange: template at (100, 80); ROI starts at (50, 40) — template inside
        image, template = pattern_image_and_template
        roi = ROIConfig(x=50, y=40, width=180, height=180)
        engine = PatternAlignEngine(threshold=0.5)

        # Act
        result = engine.align(image, template, roi=roi)

        # Assert: success and offsets are in full-image coordinates
        assert result.success, f"Expected success; got: {result.failure_reason}"
        assert abs(result.offset_x - 100.0) < 5.0
        assert abs(result.offset_y - 80.0) < 5.0

    def test_roi_excluding_template_returns_failure(self, pattern_image_and_template):
        """ROI that does not overlap the template gives a near-zero score → failure."""
        # Arrange: template at (100, 80); ROI is in the far bottom-right corner
        image, template = pattern_image_and_template
        roi = ROIConfig(x=200, y=200, width=90, height=90)
        engine = PatternAlignEngine(threshold=0.5)

        # Act
        result = engine.align(image, template, roi=roi)

        # Assert: constant-zero region → score = 0.0 < 0.5 → failure
        assert not result.success


# ═══════════════════════════════════════════════════════════════════════════════
# TestCaliperAlignEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaliperAlignEngine:
    """Standalone integration tests for CaliperAlignEngine (Sobel edge detection)."""

    def test_detects_edges_on_high_contrast_image(self, high_contrast_image):
        """Caliper engine detects the horizontal edge in a high-contrast image."""
        # Arrange
        image = high_contrast_image    # edge at y = 100
        reference = image.copy()
        engine = CaliperAlignEngine(threshold=30.0, num_calipers=8)

        # Act
        result = engine.align(image, reference)

        # Assert
        assert result.success, f"Expected success; got: {result.failure_reason}"
        assert result.score > 0.0
        assert len(result.detected_points) > 0

    def test_returns_failure_when_no_edges_present(self):
        """All-zero (blank) image has no gradient → no edges detected → failure."""
        # Arrange
        image = np.zeros((200, 200), dtype=np.uint8)
        reference = image.copy()
        engine = CaliperAlignEngine(threshold=30.0)

        # Act
        result = engine.align(image, reference)

        # Assert
        assert not result.success
        assert result.detected_points == []
        assert result.failure_reason is not None

    def test_roi_above_edge_produces_failure(self, high_contrast_image):
        """ROI that covers only the constant region above the edge → no detection."""
        # Arrange: edge at y=100; ROI covers only y=0..79 where image is zero
        image = high_contrast_image
        reference = image.copy()
        roi = ROIConfig(x=0, y=0, width=200, height=80)
        engine = CaliperAlignEngine(threshold=30.0)

        # Act
        result = engine.align(image, reference, roi_config=roi)

        # Assert: no edge in the zero-valued ROI
        assert not result.success


# ═══════════════════════════════════════════════════════════════════════════════
# TestFeatureAlignEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeatureAlignEngine:
    """Standalone integration tests for FeatureAlignEngine (ORB / SIFT)."""

    def test_keypoint_matching_on_identical_rich_texture(self, checkerboard_pair):
        """ORB matches a checkerboard reference against itself — sufficient good matches."""
        # Arrange
        ref, img = checkerboard_pair    # ref == img (same array content)
        engine = FeatureAlignEngine(min_matches=4)

        # Act
        result = engine.run(img, ref)

        # Assert
        assert result.success, f"Expected success; got: {result.failure_reason}"
        assert result.good_match_count >= 4
        assert result.score >= 0.0

    def test_returns_failure_when_insufficient_matches(self):
        """Blank images produce zero keypoints → insufficient matches → failure."""
        # Arrange
        blank = np.zeros((200, 200, 3), dtype=np.uint8)
        engine = FeatureAlignEngine(min_matches=4)

        # Act
        result = engine.run(blank, blank)

        # Assert
        assert not result.success
        assert result.good_match_count < 4
        assert result.failure_reason is not None

    def test_design_doc_contains_required_section_keys(self, checkerboard_pair):
        """FeatureAlignEngine design_doc is a dict with all four required keys."""
        # Arrange
        ref, img = checkerboard_pair
        engine = FeatureAlignEngine(min_matches=4)

        # Act
        result = engine.run(img, ref)
        doc = result.design_doc

        # Assert
        assert isinstance(doc, dict)
        for key in ("placement", "parameters", "result_calculation", "selection_rationale"):
            assert key in doc, f"Missing design_doc key: '{key}'"


# ═══════════════════════════════════════════════════════════════════════════════
# TestContourAlignEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestContourAlignEngine:
    """Standalone integration tests for ContourAlignEngine (Canny + Hu Moments)."""

    def test_contour_matching_on_identical_shapes_succeeds(self, rectangle_images):
        """Identical rectangle shapes yield matchShapes ≈ 0 → success."""
        # Arrange
        ref, img = rectangle_images
        engine = ContourAlignEngine(canny_low=50, canny_high=150)

        # Act
        result = engine.run(img, ref)

        # Assert
        assert result.success, f"Expected success; got: {result.failure_reason}"
        assert result.score >= 0.5
        assert result.match_distance < 0.5

    def test_fails_when_blank_image_has_no_contours(self):
        """Blank image produces no Canny edges → no contours → failure."""
        # Arrange
        blank = np.zeros((200, 200, 3), dtype=np.uint8)
        engine = ContourAlignEngine()

        # Act
        result = engine.run(blank, blank)

        # Assert
        assert not result.success
        assert result.failure_reason is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TestBlobAlignEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlobAlignEngine:
    """Standalone integration tests for BlobAlignEngine (SimpleBlobDetector)."""

    def test_blob_centroid_detected_successfully(self, blob_images):
        """BlobAlignEngine detects the dominant white circle blob → success, score=1.0."""
        # Arrange
        ref, img = blob_images
        engine = BlobAlignEngine(min_area=100.0, max_area=50_000.0)

        # Act
        result = engine.run(img, ref)

        # Assert
        assert result.success, f"Expected success; got: {result.failure_reason}"
        assert result.score == 1.0
        assert result.blob_area > 0.0

    def test_blob_offset_matches_known_displacement(self, blob_images):
        """Offset equals the known displacement between ref (100,100) and img (110,105)."""
        # Arrange
        ref, img = blob_images   # ref blob @ (100,100), img blob @ (110,105)
        engine = BlobAlignEngine(min_area=100.0, max_area=50_000.0)

        # Act
        result = engine.run(img, ref)

        # Assert
        assert result.success
        assert abs(result.offset_x - 10.0) < 3.0, f"offset_x={result.offset_x}"
        assert abs(result.offset_y - 5.0) < 3.0, f"offset_y={result.offset_y}"

    def test_fails_when_no_blob_in_blank_image(self):
        """All-zero image contains no white blob → failure with descriptive reason."""
        # Arrange
        blank = np.zeros((200, 200), dtype=np.uint8)
        engine = BlobAlignEngine(min_area=100.0)

        # Act
        result = engine.run(blank, blank)

        # Assert
        assert not result.success
        assert result.failure_reason is not None
        assert "No blob" in result.failure_reason


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlignFallbackChain
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlignFallbackChain:
    """End-to-end integration tests for the AlignFallbackChain orchestrator."""

    # ── Normal path ──────────────────────────────────────────────────────────

    @patch("core.align.align_engine.PatternAlignEngine")
    def test_normal_path_pattern_succeeds_first(self, MockPattern, dummy_reference):
        """Stage 1 succeeds → chain returns without trying later stages."""
        # Arrange
        MockPattern.return_value.run.return_value = _ok_result("Pattern Matching", 0.95)
        chain = _make_chain()
        image = np.zeros((100, 100), dtype=np.uint8)

        # Act
        result = chain.run(image, dummy_reference)

        # Assert
        assert result.success
        assert result.design_doc["winning_strategy"] == "pattern"
        assert result.design_doc["chain_stages_tried"] == ["pattern"]
        assert "caliper" not in result.design_doc["chain_stages_tried"]

    # ── Fallback: Pattern → Caliper ──────────────────────────────────────────

    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_fallback_pattern_fails_caliper_succeeds(
        self, MockPattern, MockCaliper, dummy_reference
    ):
        """Stage 1 fails → Stage 2 succeeds; failure_reasons records pattern failure."""
        # Arrange
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _ok_result("Caliper", 0.85)
        chain = _make_chain()
        image = np.zeros((100, 100), dtype=np.uint8)

        # Act
        result = chain.run(image, dummy_reference)

        # Assert
        assert result.success
        assert result.design_doc["winning_strategy"] == "caliper"
        assert result.design_doc["chain_stages_tried"] == ["pattern", "caliper"]
        assert "pattern" in result.design_doc["failure_reasons"]

    # ── Full fallback: all engines fail ──────────────────────────────────────

    @patch("core.align.align_engine.BlobAlignEngine")
    @patch("core.align.align_engine.ContourAlignEngine")
    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_full_fallback_all_engines_fail(
        self,
        MockPattern,
        MockCaliper,
        MockFeature,
        MockContour,
        MockBlob,
        dummy_reference,
    ):
        """All 5 engines fail → result is failure with complete accumulated failure log."""
        # Arrange
        for Mock in (MockPattern, MockCaliper, MockFeature, MockContour, MockBlob):
            Mock.return_value.run.return_value = _fail_result()
        chain = _make_chain()
        image = np.zeros((100, 100), dtype=np.uint8)

        # Act
        result = chain.run(image, dummy_reference)

        # Assert
        assert not result.success
        assert result.design_doc["winning_strategy"] == "all_failed"
        assert len(result.design_doc["failure_reasons"]) == 5
        all_stages = set(result.design_doc["chain_stages_tried"])
        assert all_stages == {"pattern", "caliper", "feature", "contour", "blob"}

    # ── AI mock path ─────────────────────────────────────────────────────────

    @patch("core.align.align_engine.FeatureAlignEngine")
    @patch("core.align.align_engine.CaliperAlignEngine")
    @patch("core.align.align_engine.PatternAlignEngine")
    def test_ai_mock_suggests_feature_strategy_and_feature_succeeds(
        self, MockPattern, MockCaliper, MockFeature, dummy_reference
    ):
        """AI is consulted after stages 1+2 fail; AI selects Feature which succeeds."""
        # Arrange: stages 1+2 fail so AI is queried
        MockPattern.return_value.run.return_value = _fail_result("Pattern Matching")
        MockCaliper.return_value.run.return_value = _fail_result("Caliper")
        MockFeature.return_value.run.return_value = _ok_result("Feature Matching", 0.88)

        mock_ai = MagicMock()
        mock_ai.complete.return_value = "feature, contour, blob"
        chain = _make_chain(ai_provider=mock_ai)
        image = np.zeros((100, 100), dtype=np.uint8)

        # Act
        result = chain.run(image, dummy_reference)

        # Assert
        assert result.success
        assert result.design_doc["winning_strategy"] == "feature"
        assert result.design_doc["ai_strategy_decision"] is True
        mock_ai.complete.assert_called_once()

    # ── Chain metadata ────────────────────────────────────────────────────────

    @patch("core.align.align_engine.PatternAlignEngine")
    def test_chain_design_doc_contains_required_metadata_keys(
        self, MockPattern, dummy_reference
    ):
        """FallbackAlignResult.design_doc always carries the four chain-level keys."""
        # Arrange
        MockPattern.return_value.run.return_value = _ok_result("Pattern Matching", 0.75)
        chain = _make_chain()
        image = np.zeros((100, 100), dtype=np.uint8)

        # Act
        result = chain.run(image, dummy_reference)
        doc = result.design_doc

        # Assert
        for key in (
            "chain_stages_tried",
            "winning_strategy",
            "failure_reasons",
            "ai_strategy_decision",
        ):
            assert key in doc, f"Missing chain metadata key: '{key}'"
        assert isinstance(doc["chain_stages_tried"], list)
        assert isinstance(doc["failure_reasons"], dict)
        assert isinstance(doc["ai_strategy_decision"], bool)


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlignDesignDocStructure
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlignDesignDocStructure:
    """Verify that every engine's design_doc output contains all 4 required sections."""

    def test_pattern_design_doc_has_four_section_markers(self):
        """PatternAlignEngine produces a string design_doc with four [Section N:] markers."""
        # Arrange
        template = _checkerboard(60, 60, block=10)
        image = np.zeros((300, 300), dtype=np.uint8)
        image[80:140, 100:160] = template
        engine = PatternAlignEngine(threshold=0.5)

        # Act
        result = engine.align(image, template)

        # Assert: string format with four labelled sections
        assert isinstance(result.design_doc, str)
        assert "[Section 1:" in result.design_doc    # arrangement / 배치 구조
        assert "[Section 2:" in result.design_doc    # parameters / 매칭 파라미터
        assert "[Section 3:" in result.design_doc    # result_calculation / 결과 계산 방식
        assert "[Section 4:" in result.design_doc    # selection_rationale / 선택 근거

    def test_caliper_design_doc_has_four_required_keys(self):
        """CaliperAlignEngine design_doc dict contains the four section keys."""
        # Arrange
        image = _high_contrast_edge()
        engine = CaliperAlignEngine(threshold=30.0)

        # Act
        result = engine.align(image, image.copy())
        doc = result.design_doc

        # Assert
        assert isinstance(doc, dict)
        assert "placement_structure" in doc      # arrangement
        assert "caliper_parameters" in doc       # parameters
        assert "result_calculation" in doc       # result_calculation
        assert "selection_rationale" in doc      # selection_rationale

    def test_feature_design_doc_has_four_required_keys(self):
        """FeatureAlignEngine design_doc dict contains the four section keys."""
        # Arrange
        ref = _checkerboard(200, 200, 20)
        engine = FeatureAlignEngine(min_matches=4)

        # Act
        result = engine.run(ref, ref)
        doc = result.design_doc

        # Assert
        assert isinstance(doc, dict)
        assert "placement" in doc               # arrangement
        assert "parameters" in doc              # parameters
        assert "result_calculation" in doc      # result_calculation
        assert "selection_rationale" in doc     # selection_rationale

    def test_contour_design_doc_has_four_required_keys(self):
        """ContourAlignEngine design_doc dict contains the four section keys."""
        # Arrange
        img = _rectangle_image()
        engine = ContourAlignEngine()

        # Act
        result = engine.run(img, img.copy())
        doc = result.design_doc

        # Assert
        assert isinstance(doc, dict)
        assert "placement" in doc
        assert "parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc

    def test_blob_design_doc_has_four_required_keys(self):
        """BlobAlignEngine design_doc dict contains the four section keys."""
        # Arrange
        img = _circle_image()
        engine = BlobAlignEngine(min_area=100.0)

        # Act
        result = engine.run(img, img.copy())
        doc = result.design_doc

        # Assert
        assert isinstance(doc, dict)
        assert "placement" in doc
        assert "parameters" in doc
        assert "result_calculation" in doc
        assert "selection_rationale" in doc
