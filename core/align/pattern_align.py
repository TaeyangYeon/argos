"""
Pattern Matching Align Engine — Stage 1 of the Argos Align Fallback Chain.

This module implements cv2.TM_CCOEFF_NORMED-based template matching as the primary
alignment strategy.  When the normalised correlation score falls below the configured
threshold the engine reports failure and the caller is expected to try the next engine
in the fallback chain (e.g. CaliperAlignEngine).

Fallback order: PatternAlignEngine → CaliperAlignEngine → FeatureAlignEngine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from core.interfaces import IAlignEngine
from core.models import AlignResult, ROIConfig


# ---------------------------------------------------------------------------
# Extended result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PatternAlignResult(AlignResult):
    """AlignResult extended with pattern-matching-specific output fields."""

    offset_x: float = 0.0
    offset_y: float = 0.0
    angle: float = 0.0
    method: str = "TM_CCOEFF_NORMED"
    design_doc: str = ""
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PatternAlignEngine(IAlignEngine):
    """
    Template matching-based alignment engine using cv2.TM_CCOEFF_NORMED.

    Implements :class:`IAlignEngine` as Stage 1 of the Argos Align Fallback Chain.
    Rotation is not computed in this stage (angle=0.0).

    Args:
        threshold: Minimum normalised correlation score to declare success.
                   Range: -1.0 ~ 1.0.  Default: 0.6.
    """

    def __init__(self, threshold: float = 0.6) -> None:
        self._threshold = threshold

    # ------------------------------------------------------------------
    # IAlignEngine interface implementation
    # ------------------------------------------------------------------

    def run(self, image: np.ndarray, reference: np.ndarray) -> PatternAlignResult:
        """Satisfy IAlignEngine.run() by delegating to align() without ROI."""
        return self.align(image, reference)

    def get_strategy_name(self) -> str:
        """Return the human-readable name of this strategy."""
        return "Pattern Matching"

    # ------------------------------------------------------------------
    # Core alignment logic
    # ------------------------------------------------------------------

    def align(
        self,
        image: np.ndarray,
        template: np.ndarray,
        roi: ROIConfig | None = None,
    ) -> PatternAlignResult:
        """
        Locate *template* inside *image* using normalised cross-correlation.

        Args:
            image: Full search image (BGR or grayscale, any dtype).
            template: Pattern to locate (BGR or grayscale, any dtype).
            roi: Optional region-of-interest that constrains the search area.
                 Offsets are reported relative to the full-image origin.

        Returns:
            :class:`PatternAlignResult` with match quality, offset, and design doc.
        """
        # --- Guard: None / empty inputs ---
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            return self._failure("image is None or empty")
        if template is None or (isinstance(template, np.ndarray) and template.size == 0):
            return self._failure("template is None or empty")

        # --- Convert to grayscale ---
        gray_image = self._to_gray(image)
        gray_template = self._to_gray(template)

        # --- Apply ROI crop ---
        roi_origin_x, roi_origin_y = 0, 0
        if roi is not None:
            gray_image = gray_image[
                roi.y : roi.y + roi.height,
                roi.x : roi.x + roi.width,
            ]
            roi_origin_x, roi_origin_y = roi.x, roi.y

        search_h, search_w = gray_image.shape[:2]
        tmpl_h, tmpl_w = gray_template.shape[:2]

        # --- Guard: template must not exceed search area ---
        if tmpl_h > search_h or tmpl_w > search_w:
            msg = (
                f"Template ({tmpl_w}×{tmpl_h}) is larger than "
                f"search area ({search_w}×{search_h})"
            )
            return self._failure(msg)

        # --- Template matching ---
        result_map = cv2.matchTemplate(
            gray_image.astype(np.float32),
            gray_template.astype(np.float32),
            cv2.TM_CCOEFF_NORMED,
        )
        _, max_val, _, max_loc = cv2.minMaxLoc(result_map)

        score = float(max_val)
        success = score >= self._threshold

        # Top-left of the matched region in full-image coordinates
        match_tl_x = float(max_loc[0]) + roi_origin_x
        match_tl_y = float(max_loc[1]) + roi_origin_y

        # Centre of matched region (full-image coords)
        match_cx = match_tl_x + tmpl_w / 2.0
        match_cy = match_tl_y + tmpl_h / 2.0

        # "offset" = where the template centre landed relative to its own centre
        # (equivalent to the top-left position in full-image coords)
        offset_x = match_cx - tmpl_w / 2.0   # == match_tl_x
        offset_y = match_cy - tmpl_h / 2.0   # == match_tl_y

        result = PatternAlignResult(
            success=success,
            strategy_name=self.get_strategy_name(),
            score=score,
            offset_x=offset_x,
            offset_y=offset_y,
            angle=0.0,
            method="TM_CCOEFF_NORMED",
            transform_matrix=np.array(
                [[1.0, 0.0, offset_x], [0.0, 1.0, offset_y]], dtype=np.float64
            ),
            failure_reason=(
                None
                if success
                else f"score {score:.4f} < threshold {self._threshold}"
            ),
            error_message=None,
        )

        result.design_doc = self.generate_design_doc(
            result=result,
            template_size=(tmpl_w, tmpl_h),
            search_size=(search_w, search_h),
        )
        return result

    # ------------------------------------------------------------------
    # Design document generation
    # ------------------------------------------------------------------

    def generate_design_doc(
        self,
        result: PatternAlignResult,
        template_size: tuple,
        search_size: tuple | None = None,
    ) -> str:
        """
        Generate the standardised 4-section design document string.

        Args:
            result: The alignment result to document.
            template_size: (width, height) of the template in pixels.
            search_size: (width, height) of the search area; defaults to (0, 0).

        Returns:
            Multi-line string with four labelled sections.
        """
        tmpl_w, tmpl_h = template_size
        sw, sh = search_size if search_size is not None else (0, 0)

        return (
            "[Section 1: 배치 구조]\n"
            f"방식: Pattern Matching (TM_CCOEFF_NORMED)\n"
            f"탐색 영역: {sw}×{sh}px\n"
            f"템플릿 크기: {tmpl_w}×{tmpl_h}px\n"
            "\n"
            "[Section 2: 매칭 파라미터]\n"
            "알고리즘: cv2.TM_CCOEFF_NORMED\n"
            f"임계값: {self._threshold}\n"
            f"결과: 매칭 점수 {result.score:.4f} / "
            f"오프셋 ({result.offset_x:.0f}, {result.offset_y:.0f})px\n"
            "\n"
            "[Section 3: 결과 계산 방식]\n"
            "최댓값 위치(minMaxLoc)→ 템플릿 중심 기준 오프셋 환산\n"
            f"성공 판정: score >= {self._threshold}\n"
            "\n"
            "[Section 4: 선택 근거]\n"
            "정규화 상관계수(TM_CCOEFF_NORMED)는 조명 변화에 강인하며\n"
            "텍스처가 풍부한 이미지에서 높은 재현성을 제공합니다.\n"
            "실패 시 Caliper Align으로 폴백됩니다."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _failure(self, message: str) -> PatternAlignResult:
        return PatternAlignResult(
            success=False,
            strategy_name=self.get_strategy_name(),
            score=0.0,
            error_message=message,
            failure_reason=message,
        )

    @staticmethod
    def _to_gray(img: np.ndarray) -> np.ndarray:
        """Convert BGR image to grayscale; pass-through if already single-channel."""
        if img.ndim == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img
