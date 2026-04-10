"""
Blob-based Align Engine — Stage 3 Fallback (Argos Align Fallback Chain).

Uses SimpleBlobDetector to locate the dominant (largest-area) blob and computes
a positional offset from a cached reference centroid.

The engine inverts the grayscale image before detection so that BRIGHT (white)
blobs on dark backgrounds are correctly located.

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
    "Keyence": "Blob measurement tool (area / centroid)",
    "Cognex": "CogBlobTool — blob detection and measurement",
    "Halcon": "blob_trans / connection / select_shape",
    "MIL": "MblobAnalyze (M_CENTER_OF_GRAVITY, M_AREA)",
}


# ─── Extended result ──────────────────────────────────────────────────────────

@dataclass
class BlobAlignResult(AlignResult):
    """AlignResult extended with blob-alignment-specific output fields."""

    design_doc: dict = field(default_factory=dict)
    overlay_image: Optional[np.ndarray] = field(default=None)
    offset_x: float = 0.0
    offset_y: float = 0.0
    blob_area: float = 0.0

    @property
    def match_score(self) -> float:
        """Alias for score (1.0 if blob found, 0.0 otherwise)."""
        return self.score


# ─── Engine ───────────────────────────────────────────────────────────────────

class BlobAlignEngine(IAlignEngine):
    """
    SimpleBlobDetector-based alignment engine.

    Implements :class:`IAlignEngine` as Stage 3C (final fallback) of the Argos
    Align Fallback Chain.

    The engine selects the blob with the **largest area** as the anchor blob.
    On the first :meth:`run` call the reference centroid is stored; subsequent
    calls compute the positional offset relative to that centroid.

    The grayscale image is **inverted** before detection so that bright
    (white) blobs on a dark background are detected correctly.

    Args:
        min_area: Minimum blob area in pixels.  Default 100.
        max_area: Maximum blob area in pixels.  Default 100000.
        min_circularity: Minimum circularity (0–1).  Disabled when 0.  Default 0.
        min_convexity: Minimum convexity (0–1).  Disabled when 0.  Default 0.
        roi: Optional ROI; image and reference are cropped before processing.
    """

    def __init__(
        self,
        min_area: float = 100.0,
        max_area: float = 100000.0,
        min_circularity: float = 0.0,
        min_convexity: float = 0.0,
        roi: Optional[ROIConfig] = None,
    ) -> None:
        self._min_area = min_area
        self._max_area = max_area
        self._min_circularity = min_circularity
        self._min_convexity = min_convexity
        self._roi = roi

        # Lazy-initialised reference state
        self._ref_initialized: bool = False
        self._ref_cx: float = 0.0
        self._ref_cy: float = 0.0
        self._ref_area: float = 0.0

        # Last overlay image
        self._last_overlay: Optional[np.ndarray] = None

    # ── IAlignEngine interface ────────────────────────────────────────────────

    def run(self, image: np.ndarray, reference: np.ndarray) -> BlobAlignResult:
        """
        Align *image* to *reference* using SimpleBlobDetector centroid matching.

        Args:
            image: Input image to align (BGR or grayscale).
            reference: Reference image used to compute (and cache) the anchor
                       blob centroid.

        Returns:
            :class:`BlobAlignResult` with success flag, score (1.0 / 0.0),
            offset, and four-section design document.
        """
        gray_img = self._to_gray(self._crop_roi(image))
        gray_ref = self._to_gray(self._crop_roi(reference))

        # Lazy initialisation from first reference image
        if not self._ref_initialized:
            self._init_reference(gray_ref)

        # ── Detect anchor blob in current image ───────────────────────────
        blob_img = self._detect_largest_blob(gray_img)

        if blob_img is None:
            return self._failure("No blob detected in image", gray_img)

        img_cx, img_cy, img_area = blob_img

        offset_x = img_cx - self._ref_cx
        offset_y = img_cy - self._ref_cy

        transform_matrix = np.array(
            [[1.0, 0.0, offset_x], [0.0, 1.0, offset_y]], dtype=np.float64
        )

        # ── Overlay ───────────────────────────────────────────────────────
        overlay = self._draw_overlay(gray_img, img_cx, img_cy, img_area)
        self._last_overlay = overlay

        design_doc = self._build_design_doc(
            found=True,
            cx=img_cx,
            cy=img_cy,
            area=img_area,
            offset_x=offset_x,
            offset_y=offset_y,
        )

        return BlobAlignResult(
            success=True,
            strategy_name=self.get_strategy_name(),
            score=1.0,
            transform_matrix=transform_matrix,
            design_doc=design_doc,
            overlay_image=overlay,
            offset_x=offset_x,
            offset_y=offset_y,
            blob_area=img_area,
        )

    def get_strategy_name(self) -> str:
        return "Blob Matching"

    def align(
        self,
        image: np.ndarray,
        reference: np.ndarray,
        roi: Optional[ROIConfig] = None,
    ) -> BlobAlignResult:
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
        """Detect and cache reference blob centroid."""
        result = self._detect_largest_blob(gray_ref)
        if result is not None:
            self._ref_cx, self._ref_cy, self._ref_area = result
        self._ref_initialized = True

    def _detect_largest_blob(
        self, gray: np.ndarray
    ) -> Optional[tuple[float, float, float]]:
        """
        Find the largest bright (white) blob in *gray* using threshold +
        findContours.  Returns (cx, cy, area) or None if no qualifying blob
        is found.

        This approach directly finds bright regions without image inversion,
        making it robust for all-black (no blob) inputs.
        """
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None

        # Filter by area
        valid = [
            c for c in contours
            if self._min_area <= cv2.contourArea(c) <= self._max_area
        ]

        # Apply optional circularity filter
        if self._min_circularity > 0:
            valid = [c for c in valid if self._circularity(c) >= self._min_circularity]

        # Apply optional convexity filter
        if self._min_convexity > 0:
            valid = [c for c in valid if self._convexity(c) >= self._min_convexity]

        if not valid:
            return None

        largest = max(valid, key=cv2.contourArea)
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        area = float(cv2.contourArea(largest))
        return cx, cy, area

    @staticmethod
    def _circularity(contour: np.ndarray) -> float:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return 0.0
        return float(4.0 * np.pi * area / (perimeter ** 2))

    @staticmethod
    def _convexity(contour: np.ndarray) -> float:
        area = cv2.contourArea(contour)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            return 0.0
        return float(area / hull_area)

    def _draw_overlay(
        self,
        gray: np.ndarray,
        cx: float,
        cy: float,
        area: float,
    ) -> np.ndarray:
        overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        radius = max(1, int(np.sqrt(area / np.pi)))
        cv2.circle(overlay, (int(cx), int(cy)), radius, (0, 255, 0), 2)
        cv2.circle(overlay, (int(cx), int(cy)), 4, (0, 0, 255), -1)
        return overlay

    def _failure(self, reason: str, gray: np.ndarray) -> BlobAlignResult:
        design_doc = self._build_design_doc(
            found=False, cx=0, cy=0, area=0, offset_x=0, offset_y=0
        )
        return BlobAlignResult(
            success=False,
            strategy_name=self.get_strategy_name(),
            score=0.0,
            failure_reason=reason,
            design_doc=design_doc,
        )

    def _build_design_doc(
        self,
        found: bool,
        cx: float,
        cy: float,
        area: float,
        offset_x: float,
        offset_y: float,
    ) -> dict:
        return {
            "placement": {
                "algorithm": "SimpleBlobDetector (centroid anchor)",
                "stage": "Stage 3C — Final fallback",
                "roi_applied": self._roi is not None,
                "library_mapping": _LIBRARY_MAPPING,
            },
            "parameters": {
                "min_area": self._min_area,
                "max_area": self._max_area,
                "min_circularity": self._min_circularity if self._min_circularity > 0 else "disabled",
                "min_convexity": self._min_convexity if self._min_convexity > 0 else "disabled",
                "image_preprocess": "cv2.bitwise_not (bright-blob inversion)",
            },
            "result_calculation": {
                "blob_found": found,
                "centroid_x": round(cx, 2),
                "centroid_y": round(cy, 2),
                "blob_area_px": round(area, 1),
                "offset_x": round(offset_x, 2),
                "offset_y": round(offset_y, 2),
                "score": 1.0 if found else 0.0,
                "score_formula": "1.0 if blob found else 0.0",
            },
            "selection_rationale": {
                "reason": (
                    "Blob detection provides robust centre-of-mass localisation "
                    "for simple circular or elliptical anchor features.  Used as "
                    "the last resort when texture and contour methods fail."
                ),
                "failure_condition": "no blob with area in [{}, {}] detected".format(
                    self._min_area, self._max_area
                ),
                "next_fallback": "None — end of fallback chain",
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
