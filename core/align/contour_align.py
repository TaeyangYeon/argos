"""
Contour-based Align Engine — Stage 3 Fallback (Argos Align Fallback Chain).

Uses Canny edge detection → findContours to locate the largest contour, then
Hu Moments (matchShapes) for shape-similarity scoring and centroid-based offset
computation.

Fallback order: PatternAlignEngine → CaliperAlignEngine
             → FeatureAlignEngine → ContourAlignEngine → BlobAlignEngine
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from core.interfaces import IAlignEngine
from core.models import AlignResult, ROIConfig

# ─── Library-name mapping ─────────────────────────────────────────────────────

_LIBRARY_MAPPING: dict[str, str] = {
    "Keyence": "Shape search tool / Edge detection tool",
    "Cognex": "CogBlobTool (blob + contour measurement)",
    "Halcon": "find_shape_model / compare_contour_xld",
    "MIL": "MedgeFindSingle / MblobAnalyze (M_SHAPE_MATCH)",
}

# Maximum matchShapes distance allowed for a successful alignment
_MAX_SHAPE_DISTANCE: float = 0.5


# ─── Extended result ──────────────────────────────────────────────────────────

@dataclass
class ContourAlignResult(AlignResult):
    """AlignResult extended with contour-matching-specific output fields."""

    design_doc: dict = field(default_factory=dict)
    overlay_image: Optional[np.ndarray] = field(default=None)
    offset_x: float = 0.0
    offset_y: float = 0.0
    match_distance: float = 1.0

    @property
    def match_score(self) -> float:
        """Alias for score (1.0 - matchShapes_distance, clamped 0–1)."""
        return self.score


# ─── Engine ───────────────────────────────────────────────────────────────────

class ContourAlignEngine(IAlignEngine):
    """
    Contour-based alignment engine using Canny + Hu Moment matching.

    Implements :class:`IAlignEngine` as Stage 3B of the Argos Align Fallback
    Chain.  Reference contour and centroid are computed lazily from the
    *reference* image on the first :meth:`run` call.

    Args:
        canny_low: Lower threshold for Canny edge detection.  Default 50.
        canny_high: Upper threshold for Canny edge detection.  Default 150.
        max_shape_distance: Maximum matchShapes distance for success.  Default 0.5.
        roi: Optional ROI; image and reference are cropped before processing.
    """

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        max_shape_distance: float = _MAX_SHAPE_DISTANCE,
        roi: Optional[ROIConfig] = None,
    ) -> None:
        self._canny_low = canny_low
        self._canny_high = canny_high
        self._max_shape_distance = max_shape_distance
        self._roi = roi

        # Lazy-initialised reference state
        self._ref_initialized: bool = False
        self._ref_contour: Optional[np.ndarray] = None
        self._ref_cx: float = 0.0
        self._ref_cy: float = 0.0

        # Last overlay image
        self._last_overlay: Optional[np.ndarray] = None

    # ── IAlignEngine interface ────────────────────────────────────────────────

    def run(self, image: np.ndarray, reference: np.ndarray) -> ContourAlignResult:
        """
        Align *image* to *reference* using contour centroid + Hu Moment matching.

        Args:
            image: Input image to align (BGR or grayscale).
            reference: Reference image used to compute (and cache) contour/centroid.

        Returns:
            :class:`ContourAlignResult` with success flag, score, offset, and
            four-section design document.
        """
        gray_img = self._to_gray(self._crop_roi(image))
        gray_ref = self._to_gray(self._crop_roi(reference))

        # Lazy initialisation
        if not self._ref_initialized:
            self._init_reference(gray_ref)

        # ── Find largest contour in the current image ─────────────────────
        img_contour = self._find_largest_contour(gray_img)

        if img_contour is None:
            return self._failure(
                "No contour found in image",
                gray_img,
                self._ref_contour,
            )

        if self._ref_contour is None:
            return self._failure(
                "No reference contour initialized",
                gray_img,
                img_contour,
            )

        # ── Shape similarity via Hu Moments ───────────────────────────────
        dist = cv2.matchShapes(
            self._ref_contour, img_contour, cv2.CONTOURS_MATCH_I1, 0
        )

        score = float(np.clip(1.0 - dist, 0.0, 1.0))

        if dist > self._max_shape_distance:
            return self._failure(
                f"matchShapes distance {dist:.4f} > threshold {self._max_shape_distance}",
                gray_img,
                img_contour,
                dist=dist,
                score=score,
            )

        # ── Centroid offset ───────────────────────────────────────────────
        img_cx, img_cy = self._centroid(img_contour)
        offset_x = img_cx - self._ref_cx
        offset_y = img_cy - self._ref_cy

        transform_matrix = np.array(
            [[1.0, 0.0, offset_x], [0.0, 1.0, offset_y]], dtype=np.float64
        )

        # ── Overlay ───────────────────────────────────────────────────────
        overlay = self._draw_overlay(gray_img, img_contour, img_cx, img_cy)
        self._last_overlay = overlay

        design_doc = self._build_design_doc(dist, score, offset_x, offset_y)

        return ContourAlignResult(
            success=True,
            strategy_name=self.get_strategy_name(),
            score=score,
            transform_matrix=transform_matrix,
            design_doc=design_doc,
            overlay_image=overlay,
            offset_x=offset_x,
            offset_y=offset_y,
            match_distance=dist,
        )

    def get_strategy_name(self) -> str:
        return "Contour Matching"

    def align(
        self,
        image: np.ndarray,
        reference: np.ndarray,
        roi: Optional[ROIConfig] = None,
    ) -> ContourAlignResult:
        """Convenience alias for run(); accepts an optional per-call ROI override."""
        if roi is not None:
            self._roi = roi
        return self.run(image, reference)

    # ── Public helpers ────────────────────────────────────────────────────────

    def save_overlay_image(self, path: str) -> None:
        """Save the last computed overlay image (BGR) to *path*."""
        if self._last_overlay is not None:
            cv2.imwrite(path, self._last_overlay)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _init_reference(self, gray_ref: np.ndarray) -> None:
        """Compute and cache the reference contour and centroid."""
        contour = self._find_largest_contour(gray_ref)
        if contour is not None:
            self._ref_contour = contour
            self._ref_cx, self._ref_cy = self._centroid(contour)
        else:
            self._ref_contour = None
        self._ref_initialized = True

    def _find_largest_contour(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """Return the largest contour by area, or None if none found."""
        edges = cv2.Canny(gray, self._canny_low, self._canny_high)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None
        return max(contours, key=cv2.contourArea)

    @staticmethod
    def _centroid(contour: np.ndarray) -> tuple[float, float]:
        M = cv2.moments(contour)
        if M["m00"] == 0:
            # Fall back to bounding-rect centre
            x, y, w, h = cv2.boundingRect(contour)
            return float(x + w / 2), float(y + h / 2)
        return M["m10"] / M["m00"], M["m01"] / M["m00"]

    def _draw_overlay(
        self,
        gray: np.ndarray,
        contour: np.ndarray,
        cx: float,
        cy: float,
    ) -> np.ndarray:
        overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        cv2.drawContours(overlay, [contour], -1, (0, 255, 0), 2)
        cv2.circle(overlay, (int(cx), int(cy)), 6, (0, 0, 255), -1)
        return overlay

    def _failure(
        self,
        reason: str,
        gray: np.ndarray,
        contour: Optional[np.ndarray],
        dist: float = 1.0,
        score: float = 0.0,
    ) -> ContourAlignResult:
        overlay: Optional[np.ndarray] = None
        if contour is not None:
            cx, cy = self._centroid(contour)
            overlay = self._draw_overlay(gray, contour, cx, cy)
            self._last_overlay = overlay

        design_doc = self._build_design_doc(dist, score, 0.0, 0.0)
        return ContourAlignResult(
            success=False,
            strategy_name=self.get_strategy_name(),
            score=score,
            failure_reason=reason,
            design_doc=design_doc,
            overlay_image=overlay,
            match_distance=dist,
        )

    def _build_design_doc(
        self,
        dist: float,
        score: float,
        offset_x: float,
        offset_y: float,
    ) -> dict:
        return {
            "placement": {
                "algorithm": "Canny Edge + Contour Hu Moments",
                "stage": "Stage 3B — Fallback after Feature Matching failure",
                "roi_applied": self._roi is not None,
                "library_mapping": _LIBRARY_MAPPING,
            },
            "parameters": {
                "canny_low": self._canny_low,
                "canny_high": self._canny_high,
                "contour_retrieval": "RETR_EXTERNAL",
                "contour_approx": "CHAIN_APPROX_SIMPLE",
                "max_shape_distance": self._max_shape_distance,
                "shape_metric": "cv2.CONTOURS_MATCH_I1 (Hu Moments)",
            },
            "result_calculation": {
                "matchShapes_distance": round(dist, 6),
                "score": round(score, 4),
                "score_formula": "1.0 - matchShapes_distance (clamped 0–1)",
                "offset_x": round(offset_x, 2),
                "offset_y": round(offset_y, 2),
            },
            "selection_rationale": {
                "reason": (
                    "Contour-based matching provides shape-level invariance to "
                    "internal texture changes.  Effective for geometric parts "
                    "with clear boundaries but low surface texture."
                ),
                "failure_condition": (
                    f"no contour found or matchShapes > {self._max_shape_distance}"
                ),
                "next_fallback": "BlobAlignEngine",
            },
        }

    def _crop_roi(self, img: np.ndarray) -> np.ndarray:
        if self._roi is None:
            return img
        r = self._roi
        return img[r.y : r.y + r.height, r.x : r.x + r.width]

    @staticmethod
    def _to_gray(img: np.ndarray) -> np.ndarray:
        if img.ndim == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img
