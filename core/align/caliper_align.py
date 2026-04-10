"""
Caliper Align Engine — Stage 2 of the Argos Align Fallback Chain.

This module implements edge-based Caliper alignment using OpenCV Sobel gradients
to detect reference edges and compute positional offsets.

Fallback order: PatternAlignEngine → CaliperAlignEngine → FeatureAlignEngine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from core.interfaces import IAlignEngine
from core.models import AlignResult, ROIConfig


# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------

class CaliperDirection(str, Enum):
    """Search direction for caliper edge detection."""
    INWARD = "Inward"
    OUTWARD = "Outward"
    LEFTWARD = "Leftward"
    RIGHTWARD = "Rightward"


class CaliperCondition(str, Enum):
    """Which edge to select when multiple are detected."""
    FIRST = "First"
    BEST = "Best"
    LAST = "Last"
    ALL = "All"


class CaliperPolarity(str, Enum):
    """Edge transition polarity filter."""
    DARK_TO_LIGHT = "Dark-to-Light"
    LIGHT_TO_DARK = "Light-to-Dark"
    EITHER = "Either"


# ---------------------------------------------------------------------------
# Extended result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CaliperAlignResult(AlignResult):
    """AlignResult extended with caliper-specific output fields."""

    offset_x: float = 0.0
    offset_y: float = 0.0
    angle: float = 0.0
    method: str = "Caliper (Sobel)"
    design_doc: dict = field(default_factory=dict)
    overlay_image: Optional[np.ndarray] = field(default=None)
    detected_points: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CaliperAlignEngine(IAlignEngine):
    """
    Edge-based alignment engine using Sobel gradient caliper detection.

    Implements :class:`IAlignEngine` as Stage 2 of the Argos Align Fallback Chain.

    Args:
        projection_length: Length of caliper probe perpendicular to search direction (px).
        search_length: Distance searched along detection direction (px).
        condition: Which detected edge to use (First / Best / Last / All).
        threshold: Minimum gradient magnitude to accept an edge (0–255).
        polarity: Edge transition polarity filter.
        direction: Search direction (Inward / Outward / Leftward / Rightward).
        num_calipers: Number of caliper probes placed along the reference edge.
        roi_config: Optional region-of-interest that constrains the search area.
    """

    def __init__(
        self,
        projection_length: int = 20,
        search_length: int = 200,
        condition: CaliperCondition = CaliperCondition.BEST,
        threshold: float = 30.0,
        polarity: CaliperPolarity = CaliperPolarity.EITHER,
        direction: CaliperDirection = CaliperDirection.INWARD,
        num_calipers: int = 8,
        roi_config: Optional[ROIConfig] = None,
    ) -> None:
        self._projection_length = projection_length
        self._search_length = search_length
        self._condition = condition
        self._threshold = threshold
        self._polarity = polarity
        self._direction = direction
        self._num_calipers = num_calipers
        self._roi_config = roi_config

    # ------------------------------------------------------------------
    # IAlignEngine interface implementation
    # ------------------------------------------------------------------

    def run(self, image: np.ndarray, reference: np.ndarray) -> CaliperAlignResult:
        """Satisfy IAlignEngine.run() by delegating to align()."""
        return self.align(image, reference)

    def get_strategy_name(self) -> str:
        return "Caliper"

    # ------------------------------------------------------------------
    # Core alignment logic
    # ------------------------------------------------------------------

    def align(
        self,
        image: np.ndarray,
        reference: np.ndarray,
        roi_config: Optional[ROIConfig] = None,
    ) -> CaliperAlignResult:
        """
        Detect edges in *image* relative to *reference* and compute offset.

        Args:
            image: Full input image (BGR or grayscale, uint8).
            reference: Reference image used for image metrics in design_doc.
            roi_config: Optional ROI; overrides constructor roi_config if provided.

        Returns:
            :class:`CaliperAlignResult` with edge positions, offset, and design doc.
        """
        active_roi = roi_config if roi_config is not None else self._roi_config

        # --- Guard: None / empty inputs ---
        if image is None or (isinstance(image, np.ndarray) and image.size == 0):
            return self._failure("image is None or empty", image)

        # --- Convert to grayscale ---
        gray = self._to_gray(image)

        # --- Apply ROI ---
        roi_origin_x, roi_origin_y = 0, 0
        if active_roi is not None:
            gray = gray[
                active_roi.y: active_roi.y + active_roi.height,
                active_roi.x: active_roi.x + active_roi.width,
            ]
            roi_origin_x, roi_origin_y = active_roi.x, active_roi.y

        h, w = gray.shape[:2]

        # --- Compute image-level metrics for design_doc section 4 ---
        mean_gray = float(np.mean(gray))
        std_gray = float(np.std(gray))
        contrast = float(np.max(gray) - np.min(gray))

        # --- Detect edges ---
        detected_points = self.detect_edges(gray)

        # --- Populate design_doc with all 4 sections (even on failure) ---
        design_doc = self._build_design_doc(
            image_h=h,
            image_w=w,
            mean_gray=mean_gray,
            std_gray=std_gray,
            contrast=contrast,
            detected_count=len(detected_points),
            roi_origin_x=roi_origin_x,
            roi_origin_y=roi_origin_y,
        )

        if not detected_points:
            result = CaliperAlignResult(
                success=False,
                strategy_name=self.get_strategy_name(),
                score=0.0,
                failure_reason="No valid edges detected above threshold",
                design_doc=design_doc,
                overlay_image=None,
                detected_points=[],
            )
            return result

        # --- Compute offset from detected edge centroid ---
        pts = np.array(detected_points, dtype=np.float64)
        centroid_x = float(np.mean(pts[:, 0])) + roi_origin_x
        centroid_y = float(np.mean(pts[:, 1])) + roi_origin_y

        # Reference centroid (centre of full image)
        ref_cx = w / 2.0 + roi_origin_x
        ref_cy = h / 2.0 + roi_origin_y

        offset_x = centroid_x - ref_cx
        offset_y = centroid_y - ref_cy

        # Score: fraction of calipers that found a valid edge, normalised
        score = min(1.0, len(detected_points) / max(1, self._num_calipers))

        # --- Build overlay image ---
        overlay = self._draw_overlay(image, detected_points, roi_origin_x, roi_origin_y)

        # --- Update design_doc section 3 with actual results ---
        design_doc["result_calculation"]["centroid_x"] = round(centroid_x, 2)
        design_doc["result_calculation"]["centroid_y"] = round(centroid_y, 2)
        design_doc["result_calculation"]["offset_x"] = round(offset_x, 2)
        design_doc["result_calculation"]["offset_y"] = round(offset_y, 2)
        design_doc["result_calculation"]["valid_edge_count"] = len(detected_points)
        design_doc["result_calculation"]["score"] = round(score, 4)

        transform_matrix = np.array(
            [[1.0, 0.0, offset_x], [0.0, 1.0, offset_y]], dtype=np.float64
        )

        return CaliperAlignResult(
            success=True,
            strategy_name=self.get_strategy_name(),
            score=score,
            transform_matrix=transform_matrix,
            offset_x=offset_x,
            offset_y=offset_y,
            angle=0.0,
            method="Caliper (Sobel)",
            design_doc=design_doc,
            overlay_image=overlay,
            detected_points=detected_points,
        )

    # ------------------------------------------------------------------
    # Edge detection (independently testable)
    # ------------------------------------------------------------------

    def detect_edges(self, gray: np.ndarray) -> list[tuple[int, int]]:
        """
        Detect edge points in *gray* using Sobel gradient magnitude.

        Caliper probes are distributed along the axis perpendicular to the
        configured direction, and each probe scans along the detection direction
        to find the strongest gradient peak above *threshold*.

        Args:
            gray: Single-channel uint8 grayscale image.

        Returns:
            List of (x, y) pixel coordinates of detected edge points
            (in the coordinate frame of *gray*, i.e. within the ROI if one was applied).
        """
        if gray is None or gray.size == 0:
            return []

        h, w = gray.shape[:2]

        # --- Compute Sobel gradient magnitude ---
        sobel_x = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)

        # Apply polarity filter to signed gradient
        if self._polarity == CaliperPolarity.DARK_TO_LIGHT:
            # Positive gradients only (intensity rising)
            if self._direction in (CaliperDirection.RIGHTWARD, CaliperDirection.INWARD):
                signed = sobel_x
            else:
                signed = sobel_y
            magnitude = np.where(signed > 0, magnitude, 0.0)
        elif self._polarity == CaliperPolarity.LIGHT_TO_DARK:
            # Negative gradients only (intensity falling)
            if self._direction in (CaliperDirection.RIGHTWARD, CaliperDirection.INWARD):
                signed = sobel_x
            else:
                signed = sobel_y
            magnitude = np.where(signed < 0, magnitude, 0.0)
        # CaliperPolarity.EITHER: keep full magnitude

        detected: list[tuple[int, int]] = []

        # Distribute caliper probes
        is_horizontal = self._direction in (
            CaliperDirection.LEFTWARD, CaliperDirection.RIGHTWARD
        )

        if is_horizontal:
            # Probes distributed vertically, scan horizontally
            probe_positions = np.linspace(
                self._projection_length // 2,
                h - self._projection_length // 2,
                self._num_calipers,
                dtype=int,
            )
            for row in probe_positions:
                row = int(np.clip(row, 0, h - 1))
                half_proj = self._projection_length // 2
                r_start = max(0, row - half_proj)
                r_end = min(h, row + half_proj + 1)

                # Sum magnitude over projection band
                band = magnitude[r_start:r_end, :]
                profile = np.mean(band, axis=0)

                if self._direction == CaliperDirection.RIGHTWARD:
                    scan_start = 0
                    scan_end = min(w, self._search_length)
                else:  # LEFTWARD
                    scan_start = max(0, w - self._search_length)
                    scan_end = w

                profile_slice = profile[scan_start:scan_end]
                pt = self._select_edge(profile_slice, scan_start, row)
                if pt is not None:
                    detected.append(pt)
        else:
            # Probes distributed horizontally, scan vertically
            probe_positions = np.linspace(
                self._projection_length // 2,
                w - self._projection_length // 2,
                self._num_calipers,
                dtype=int,
            )
            for col in probe_positions:
                col = int(np.clip(col, 0, w - 1))
                half_proj = self._projection_length // 2
                c_start = max(0, col - half_proj)
                c_end = min(w, col + half_proj + 1)

                band = magnitude[:, c_start:c_end]
                profile = np.mean(band, axis=1)

                if self._direction == CaliperDirection.INWARD:
                    scan_start = 0
                    scan_end = min(h, self._search_length)
                else:  # OUTWARD
                    scan_start = max(0, h - self._search_length)
                    scan_end = h

                profile_slice = profile[scan_start:scan_end]
                pt = self._select_edge(profile_slice, col, scan_start, vertical=True)
                if pt is not None:
                    detected.append(pt)

        return detected

    def _select_edge(
        self,
        profile: np.ndarray,
        col_or_offset: int,
        row_or_col: int,
        vertical: bool = False,
    ) -> Optional[tuple[int, int]]:
        """
        Select an edge position from a 1-D gradient magnitude profile.

        Args:
            profile: 1-D array of gradient magnitudes along the scan direction.
            col_or_offset: For horizontal scan: start column offset;
                           for vertical scan: column index of probe.
            row_or_col: For horizontal scan: row index of probe;
                        for vertical scan: start row offset.
            vertical: True when scanning vertically (INWARD/OUTWARD).

        Returns:
            (x, y) pixel coordinate, or None if no edge above threshold found.
        """
        if len(profile) == 0:
            return None

        above = np.where(profile >= self._threshold)[0]
        if len(above) == 0:
            return None

        if self._condition == CaliperCondition.FIRST:
            idx = int(above[0])
        elif self._condition == CaliperCondition.LAST:
            idx = int(above[-1])
        elif self._condition == CaliperCondition.BEST:
            # Best = highest magnitude among candidates
            candidate_vals = profile[above]
            idx = int(above[np.argmax(candidate_vals)])
        else:  # ALL — return the one with highest magnitude (simplified single-pt)
            candidate_vals = profile[above]
            idx = int(above[np.argmax(candidate_vals)])

        if vertical:
            # col_or_offset = probe column, row_or_col = scan row start offset
            x = col_or_offset
            y = row_or_col + idx
        else:
            # col_or_offset = scan col start offset, row_or_col = probe row
            x = col_or_offset + idx
            y = row_or_col

        return (int(x), int(y))

    # ------------------------------------------------------------------
    # Design document generation
    # ------------------------------------------------------------------

    def _build_design_doc(
        self,
        image_h: int,
        image_w: int,
        mean_gray: float,
        std_gray: float,
        contrast: float,
        detected_count: int,
        roi_origin_x: int,
        roi_origin_y: int,
    ) -> dict:
        """Build all 4 design document sections."""

        section1 = {
            "arrangement_type": "Linear caliper array",
            "count": self._num_calipers,
            "spacing_px": (
                (image_h if self._direction in (CaliperDirection.INWARD, CaliperDirection.OUTWARD)
                 else image_w) // max(1, self._num_calipers - 1)
            ),
            "start_position": "Image border (direction-dependent)",
            "reference_point": f"Image centre ({image_w // 2 + roi_origin_x}, "
                               f"{image_h // 2 + roi_origin_y})",
            "search_direction": self._direction.value,
            "search_area_px": f"{image_w}×{image_h}",
        }

        section2 = {
            "projection_length": self._projection_length,
            "search_length": self._search_length,
            "condition": self._condition.value,
            "threshold": self._threshold,
            "polarity": self._polarity.value,
            "edge_filter": "Sobel (ksize=3)",
        }

        section3 = {
            "mapping_method": "Edge centroid of detected points → offset from image centre",
            "outlier_handling": "Points below threshold excluded; centroid of survivors used",
            "confidence_criteria": f"score = valid_edges / num_calipers (≥ 1.0 = full coverage)",
            "centroid_x": "N/A",
            "centroid_y": "N/A",
            "offset_x": "N/A",
            "offset_y": "N/A",
            "valid_edge_count": detected_count,
            "score": "N/A",
        }

        section4 = {
            "mean_gray": round(mean_gray, 2),
            "std_gray": round(std_gray, 2),
            "contrast": round(contrast, 2),
            "image_size_px": f"{image_w}×{image_h}",
            "direction_chosen": self._direction.value,
            "rationale": (
                f"Sobel-based caliper chosen because contrast={contrast:.1f} "
                f"(threshold={self._threshold}) provides sufficient edge signal. "
                f"Direction '{self._direction.value}' aligns with expected part orientation. "
                f"Used as Stage 2 fallback after Pattern Matching."
            ),
        }

        return {
            "placement_structure": section1,
            "caliper_parameters": section2,
            "result_calculation": section3,
            "selection_rationale": section4,
        }

    # ------------------------------------------------------------------
    # Overlay image generation
    # ------------------------------------------------------------------

    def _draw_overlay(
        self,
        image: np.ndarray,
        detected_points: list[tuple[int, int]],
        roi_origin_x: int,
        roi_origin_y: int,
    ) -> np.ndarray:
        """Draw detected edge points as coloured circles on the input image."""
        if image.ndim == 2:
            overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            overlay = image.copy()

        for (x, y) in detected_points:
            # Translate back to full-image coordinates
            fx = x + roi_origin_x
            fy = y + roi_origin_y
            cv2.circle(overlay, (fx, fy), radius=4, color=(0, 255, 0), thickness=-1)
            cv2.circle(overlay, (fx, fy), radius=5, color=(0, 128, 0), thickness=1)

        return overlay

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _failure(self, message: str, image: Optional[np.ndarray]) -> CaliperAlignResult:
        """Return a failure result with populated (empty) design_doc."""
        design_doc = {
            "placement_structure": {
                "arrangement_type": "N/A",
                "count": self._num_calipers,
                "spacing_px": "N/A",
                "start_position": "N/A",
                "reference_point": "N/A",
                "search_direction": self._direction.value,
                "search_area_px": "N/A",
            },
            "caliper_parameters": {
                "projection_length": self._projection_length,
                "search_length": self._search_length,
                "condition": self._condition.value,
                "threshold": self._threshold,
                "polarity": self._polarity.value,
                "edge_filter": "Sobel (ksize=3)",
            },
            "result_calculation": {
                "mapping_method": "N/A",
                "outlier_handling": "N/A",
                "confidence_criteria": "N/A",
                "centroid_x": "N/A",
                "centroid_y": "N/A",
                "offset_x": "N/A",
                "offset_y": "N/A",
                "valid_edge_count": 0,
                "score": "N/A",
            },
            "selection_rationale": {
                "mean_gray": "N/A",
                "std_gray": "N/A",
                "contrast": "N/A",
                "image_size_px": "N/A",
                "direction_chosen": self._direction.value,
                "rationale": f"Failed: {message}",
            },
        }
        return CaliperAlignResult(
            success=False,
            strategy_name=self.get_strategy_name(),
            score=0.0,
            failure_reason=message,
            design_doc=design_doc,
            overlay_image=None,
            detected_points=[],
        )

    @staticmethod
    def _to_gray(img: np.ndarray) -> np.ndarray:
        """Convert BGR image to grayscale; pass-through if already single-channel."""
        if img.ndim == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img
