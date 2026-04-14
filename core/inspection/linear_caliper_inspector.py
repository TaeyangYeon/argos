"""
Linear Caliper Inspection Engine (Argos Step 36).

Places N calipers in a linear array (horizontal or vertical), extracts 1D
Sobel gradient profiles along the search direction, detects edges, and
computes width / straightness / parallelism measurements.

CPU-only — NumPy and OpenCV only. No scikit-image, no scipy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from core.inspection.circular_caliper_inspector import (
    CaliperCondition,
    CaliperPolarity,
)
from core.models import InspectionCandidate, InspectionPurpose, InspectionResult, ROIConfig

logger = logging.getLogger("argos.inspection.linear_caliper")


# ─── Enumerations ─────────────────────────────────────────────────────────────

class LinearCaliperDirection(str, Enum):
    """Search direction for each linear caliper strip."""

    LEFTWARD  = "Leftward"
    RIGHTWARD = "Rightward"
    UPWARD    = "Upward"
    DOWNWARD  = "Downward"


# ─── Candidate descriptor ─────────────────────────────────────────────────────

@dataclass
class LinearCaliperPreset:
    """Parameter preset for one linear-caliper candidate."""

    caliper_count: int
    direction: LinearCaliperDirection
    condition: CaliperCondition
    polarity: CaliperPolarity
    search_length: int
    projection_length: int
    threshold_factor: float = 1.5

    def to_dict(self) -> dict:
        """Serialise to a plain JSON-compatible dict."""
        return {
            "caliper_count":     self.caliper_count,
            "direction":         self.direction.value,
            "condition":         self.condition.value,
            "polarity":          self.polarity.value,
            "search_length":     self.search_length,
            "projection_length": self.projection_length,
            "threshold_factor":  self.threshold_factor,
        }


# ─── Helper functions ─────────────────────────────────────────────────────────

def _to_gray(image: np.ndarray) -> np.ndarray:
    """Convert BGR or grayscale image to single-channel uint8."""
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image.copy()


def _crop_roi(image: np.ndarray, roi: Optional[ROIConfig]) -> np.ndarray:
    """Crop image to ROI if provided; otherwise return unchanged."""
    if roi is None:
        return image
    return image[roi.y: roi.y + roi.height, roi.x: roi.x + roi.width]


def _is_horizontal(direction: LinearCaliperDirection) -> bool:
    """Return True if the direction scans along the X axis."""
    return direction in (LinearCaliperDirection.RIGHTWARD, LinearCaliperDirection.LEFTWARD)


# ─── Core numerical routines ──────────────────────────────────────────────────

def _find_edge(
    profile: np.ndarray,
    condition: CaliperCondition,
    polarity: CaliperPolarity,
    threshold_factor: float,
) -> Optional[int]:
    """
    Find a single edge position in a 1D intensity profile.

    A Sobel-like kernel is convolved with the profile to approximate the
    first derivative. The threshold is set dynamically as
    ``mean(|gradient|) + threshold_factor * std(|gradient|)``.

    Args:
        profile:          1D float32 intensity array.
        condition:        FIRST / BEST / LAST — which gradient peak to select.
        polarity:         BRIGHTER looks for dark→bright transitions; DARKER
                          looks for bright→dark transitions.
        threshold_factor: Controls the dynamic threshold sensitivity.

    Returns:
        Integer index of the detected edge within *profile*, or ``None`` if
        no edge exceeds the threshold.
    """
    if len(profile) < 3:
        return None

    kernel = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
    gradient = np.convolve(profile, kernel, mode="same")

    if polarity == CaliperPolarity.DARKER:
        gradient = -gradient

    abs_g = np.abs(gradient)
    threshold = float(np.mean(abs_g)) + threshold_factor * float(np.std(abs_g))

    peaks = np.where(gradient > threshold)[0]

    if len(peaks) == 0:
        # Fallback: use the global maximum if it is positive
        best = int(np.argmax(gradient))
        return best if gradient[best] > 0 else None

    if condition == CaliperCondition.FIRST:
        return int(peaks[0])
    if condition == CaliperCondition.LAST:
        return int(peaks[-1])
    # BEST and ALL both select the strongest peak
    return int(peaks[int(np.argmax(gradient[peaks]))])


def _extract_profile_1d(
    gray: np.ndarray,
    pos: int,
    horizontal: bool,
    projection_length: int,
) -> np.ndarray:
    """
    Extract a 1D intensity profile by averaging a narrow strip perpendicular
    to the search direction.

    Args:
        gray:             Single-channel uint8 image.
        pos:              Row index (if *horizontal* is True) or column index
                          of the caliper centre.
        horizontal:       If True, the profile runs along the X axis;
                          otherwise along the Y axis.
        projection_length: Half-width of the averaging strip in pixels.

    Returns:
        1D float32 array of length W (horizontal) or H (vertical).
    """
    h, w = gray.shape[:2]
    half = max(1, projection_length // 2)

    if horizontal:
        r0 = max(0, pos - half)
        r1 = min(h, pos + half + 1)
        strip = gray[r0:r1, :]
        return np.mean(strip, axis=0).astype(np.float32)
    else:
        c0 = max(0, pos - half)
        c1 = min(w, pos + half + 1)
        strip = gray[:, c0:c1]
        return np.mean(strip, axis=1).astype(np.float32)


def _find_both_edges(
    gray: np.ndarray,
    pos: int,
    horizontal: bool,
    projection_length: int,
    condition: CaliperCondition,
    polarity: CaliperPolarity,
    threshold_factor: float,
) -> tuple[Optional[int], Optional[int]]:
    """
    Find the two opposing edges (near and far) of an object at caliper position.

    The near edge is found by scanning the profile forward; the far edge is
    found by reversing the profile so that a BRIGHTER polarity still picks up
    the correct transition.

    Args:
        gray:              Single-channel image.
        pos:               Caliper placement coordinate.
        horizontal:        If True, search along X; otherwise along Y.
        projection_length: Averaging strip half-width.
        condition:         Edge selection condition.
        polarity:          Expected edge polarity.
        threshold_factor:  Dynamic threshold sensitivity.

    Returns:
        (near_pos, far_pos) in image pixel coordinates, either value may be
        None if no edge was detected.
    """
    profile = _extract_profile_1d(gray, pos, horizontal, projection_length)
    profile_len = len(profile)

    # Near edge: scan forward
    idx_near = _find_edge(profile, condition, polarity, threshold_factor)

    # Far edge: reverse the profile so the far transition appears as near
    idx_far_rev = _find_edge(profile[::-1], condition, polarity, threshold_factor)
    idx_far = (profile_len - 1 - idx_far_rev) if idx_far_rev is not None else None

    # Sanity-check: near must be strictly less than far
    if idx_near is not None and idx_far is not None and idx_near >= idx_far:
        # Swap if inverted (can happen when both gradients are in the same region)
        idx_near, idx_far = min(idx_near, idx_far), max(idx_near, idx_far)
        if idx_near == idx_far:
            return None, None

    return idx_near, idx_far


def _reject_linear_outliers(
    values: list[float],
) -> list[bool]:
    """
    Compute a boolean mask that is True for inlier values (within 3σ of mean).

    Args:
        values: List of float measurement values.

    Returns:
        List of booleans, same length as *values*. True = inlier.
    """
    if len(values) < 2:
        return [True] * len(values)

    arr = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(arr))
    sigma = float(np.std(arr))
    threshold = 3.0 * sigma
    return [bool(abs(v - mean) <= threshold + 1e-9) for v in values]


def _compute_measurements(
    gray: np.ndarray,
    preset: LinearCaliperPreset,
) -> dict:
    """
    Place calipers, detect edges, remove 3σ outliers, and compute metrics.

    Metrics computed:
    - ``mean_width``   : average distance between paired near/far edges (px).
    - ``straightness`` : std deviation of near-edge positions (px).
    - ``parallelism``  : max residual from a linear fit to near/far edge lines.

    Args:
        gray:   Single-channel uint8 image (already ROI-cropped).
        preset: LinearCaliperPreset describing the caliper parameters.

    Returns:
        Dict with keys: valid_count, caliper_positions, edge1_positions,
        edge2_positions, widths, mean_width, straightness, parallelism,
        is_horizontal.
    """
    h, w = gray.shape[:2]
    horizontal = _is_horizontal(preset.direction)

    # Placement: spread evenly with a margin of 1/8 of the placement-axis length
    axis_len = h if horizontal else w
    margin = max(1, axis_len // 8)
    positions = list(
        np.linspace(margin, axis_len - margin, preset.caliper_count, dtype=int)
    )

    raw_positions: list[int] = []
    raw_e1: list[int] = []
    raw_e2: list[int] = []

    for pos in positions:
        e1, e2 = _find_both_edges(
            gray, pos, horizontal,
            preset.projection_length, preset.condition,
            preset.polarity, preset.threshold_factor,
        )
        if e1 is not None and e2 is not None and e2 > e1:
            raw_positions.append(pos)
            raw_e1.append(e1)
            raw_e2.append(e2)

    # 3σ outlier removal on widths
    widths = [float(e2 - e1) for e1, e2 in zip(raw_e1, raw_e2)]
    mask = _reject_linear_outliers(widths)

    caliper_positions = [p for p, m in zip(raw_positions, mask) if m]
    edge1_positions   = [e for e, m in zip(raw_e1, mask) if m]
    edge2_positions   = [e for e, m in zip(raw_e2, mask) if m]
    widths_filtered   = [wt for wt, m in zip(widths, mask) if m]

    valid_count = len(widths_filtered)
    mean_width  = float(np.mean(widths_filtered)) if widths_filtered else 0.0

    # Straightness: std of near-edge positions
    straightness = float(np.std(edge1_positions)) if len(edge1_positions) >= 2 else 0.0

    # Parallelism: max residual from linear fit to each edge line
    parallelism = 0.0
    if len(caliper_positions) >= 2:
        xs  = np.array(caliper_positions, dtype=np.float64)
        y1s = np.array(edge1_positions,   dtype=np.float64)
        y2s = np.array(edge2_positions,   dtype=np.float64)

        coef1 = np.polyfit(xs, y1s, 1)
        coef2 = np.polyfit(xs, y2s, 1)

        dev1 = float(np.max(np.abs(y1s - np.polyval(coef1, xs))))
        dev2 = float(np.max(np.abs(y2s - np.polyval(coef2, xs))))
        parallelism = max(dev1, dev2)

    return {
        "valid_count":       valid_count,
        "caliper_positions": caliper_positions,
        "edge1_positions":   edge1_positions,
        "edge2_positions":   edge2_positions,
        "widths":            widths_filtered,
        "mean_width":        mean_width,
        "straightness":      straightness,
        "parallelism":       parallelism,
        "is_horizontal":     horizontal,
    }


def _draw_overlay(
    image: np.ndarray,
    measurements: dict,
    direction: LinearCaliperDirection,
) -> np.ndarray:
    """
    Draw detected edge points (green dots) and fitted edge lines (colored)
    on a copy of *image*.

    Args:
        image:        Source image (BGR or grayscale).
        measurements: Output of :func:`_compute_measurements`.
        direction:    Search direction (used for coordinate mapping).

    Returns:
        BGR uint8 ndarray with annotations.
    """
    overlay = image.copy()
    if overlay.ndim == 2:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

    horizontal = measurements.get("is_horizontal", True)
    caliper_positions = measurements.get("caliper_positions", [])
    edge1_positions   = measurements.get("edge1_positions",   [])
    edge2_positions   = measurements.get("edge2_positions",   [])

    h, w = overlay.shape[:2]

    # Draw edge points
    for i, pos in enumerate(caliper_positions):
        if i < len(edge1_positions):
            e1 = edge1_positions[i]
            pt1 = (int(e1), int(pos)) if horizontal else (int(pos), int(e1))
            cv2.circle(overlay, pt1, 4, (0, 255, 0), -1)

        if i < len(edge2_positions):
            e2 = edge2_positions[i]
            pt2 = (int(e2), int(pos)) if horizontal else (int(pos), int(e2))
            cv2.circle(overlay, pt2, 4, (0, 200, 50), -1)

    # Draw linear-fit lines
    if len(caliper_positions) >= 2:
        xs = np.array(caliper_positions, dtype=np.float64)

        for edges, color in [
            (edge1_positions, (0, 255, 0)),
            (edge2_positions, (0, 165, 255)),
        ]:
            if len(edges) < 2:
                continue
            es = np.array(edges, dtype=np.float64)
            coef = np.polyfit(xs, es, 1)

            p_min, p_max = int(xs.min()), int(xs.max())
            e_min = int(np.clip(np.polyval(coef, p_min), 0, (w if horizontal else h) - 1))
            e_max = int(np.clip(np.polyval(coef, p_max), 0, (w if horizontal else h) - 1))

            if horizontal:
                pt_a = (e_min, p_min)
                pt_b = (e_max, p_max)
            else:
                pt_a = (p_min, e_min)
                pt_b = (p_max, e_max)

            cv2.line(overlay, pt_a, pt_b, color, 2)

    return overlay


def _build_library_mapping(preset: LinearCaliperPreset) -> dict:
    """
    Return a Keyence / Cognex / Halcon / MIL parameter-name translation table.

    Args:
        preset: LinearCaliperPreset whose parameters fill concrete values.

    Returns:
        Nested dict keyed by library name, compatible with the 4-vendor format.
    """
    cond_map = {
        CaliperCondition.FIRST: ("첫 번째 에지", "First", "'first'", "M_FIRST_CONTRAST"),
        CaliperCondition.BEST:  ("최적 에지",    "Best",  "'best'",  "M_BEST_CONTRAST"),
        CaliperCondition.LAST:  ("마지막 에지",  "Last",  "'last'",  "M_LAST_CONTRAST"),
        CaliperCondition.ALL:   ("모든 에지",    "All",   "'all'",   "M_ALL_CONTRAST"),
    }
    dir_map = {
        LinearCaliperDirection.RIGHTWARD: ("우방향", "Rightward", "'right'", "M_RIGHTWARD"),
        LinearCaliperDirection.LEFTWARD:  ("좌방향", "Leftward",  "'left'",  "M_LEFTWARD"),
        LinearCaliperDirection.DOWNWARD:  ("하방향", "Downward",  "'down'",  "M_DOWNWARD"),
        LinearCaliperDirection.UPWARD:    ("상방향", "Upward",    "'up'",    "M_UPWARD"),
    }

    kc, coc, hc, mc = cond_map[preset.condition]
    kd, cod, hd, md = dir_map[preset.direction]

    return {
        "concept_table": {
            "Search Length": {
                "Keyence": f"탐색 폭 = {preset.search_length}px",
                "Cognex":  f"SearchLength = {preset.search_length}",
                "Halcon":  f"SearchExtent = {preset.search_length}",
                "MIL":     f"M_SEARCH_LENGTH = {preset.search_length}",
            },
            "Projection Length": {
                "Keyence": f"투영 길이 = {preset.projection_length}px",
                "Cognex":  f"ProjectionLength = {preset.projection_length}",
                "Halcon":  f"ProfileLength = {preset.projection_length}",
                "MIL":     f"M_PROJECTION_LENGTH = {preset.projection_length}",
            },
            "Condition": {
                "Keyence": kc, "Cognex": coc, "Halcon": hc, "MIL": mc,
            },
            "Direction": {
                "Keyence": kd, "Cognex": cod, "Halcon": hd, "MIL": md,
            },
            "Caliper Count": {
                "Keyence": f"Caliper 수 = {preset.caliper_count}",
                "Cognex":  f"NumCalipers = {preset.caliper_count}",
                "Halcon":  f"NumMeasureObjects = {preset.caliper_count}",
                "MIL":     f"M_CALIPER_COUNT = {preset.caliper_count}",
            },
        }
    }


def _build_design_doc(
    preset: LinearCaliperPreset,
    measurements: dict,
    h: int,
    w: int,
) -> dict:
    """
    Build the mandatory 4-section design document for one candidate.

    Sections:
      1. ``placement``          — arrangement type, count, spacing, direction.
      2. ``caliper_params``     — per-caliper parameters (search/projection length,
                                  condition, polarity, threshold).
      3. ``result_calculation`` — metric formulas, outlier criteria, result values.
      4. ``rationale``          — image-analysis basis and design choices.

    Args:
        preset:       LinearCaliperPreset used.
        measurements: Output of :func:`_compute_measurements`.
        h, w:         Image height and width (after ROI crop).

    Returns:
        JSON-serialisable dict with keys: placement, caliper_params,
        result_calculation, rationale, library_mapping, warnings.
    """
    horizontal  = measurements.get("is_horizontal", True)
    valid_count = measurements.get("valid_count", 0)
    mean_width  = measurements.get("mean_width", 0.0)
    straightness = measurements.get("straightness", 0.0)
    parallelism  = measurements.get("parallelism", 0.0)

    axis_len  = h if horizontal else w
    n_gaps    = max(preset.caliper_count - 1, 1)
    spacing   = round((axis_len * 0.75) / n_gaps, 1)

    warnings: list[str] = []
    if valid_count < 4:
        warnings.append(
            f"유효 Caliper 수 부족 ({valid_count}개 < 4개) — 신뢰도 낮음"
        )

    cond_rationale_map = {
        CaliperCondition.FIRST: "탐색 시작점에서 첫 에지 선택, 노이즈 적은 환경에 유리",
        CaliperCondition.BEST:  "최대 그래디언트 에지 선택, 대비 좋은 환경에서 가장 안정적",
        CaliperCondition.LAST:  "마지막 에지 선택, 이중 에지 환경에서 외곽 선택 시 사용",
        CaliperCondition.ALL:   "모든 에지 평균, 다층 구조 이미지에 적합",
    }

    return {
        "placement": {
            "arrangement":   "수평 배열" if horizontal else "수직 배열",
            "caliper_count": preset.caliper_count,
            "spacing_px":    spacing,
            "direction":     preset.direction.value,
            "placement_axis": "Y축" if horizontal else "X축",
            "search_axis":    "X축" if horizontal else "Y축",
        },
        "caliper_params": {
            "search_length_px":    preset.search_length,
            "projection_length_px": preset.projection_length,
            "condition":           preset.condition.value,
            "polarity":            preset.polarity.value,
            "threshold_factor":    preset.threshold_factor,
            "edge_filter":         "Sobel 1D along search direction",
        },
        "result_calculation": {
            "method":              "Linear edge fit (np.polyfit degree=1)",
            "outlier_rejection":   "3σ width deviation removal",
            "confidence_condition": "valid_caliper_count >= 4",
            "valid_caliper_count": valid_count,
            "mean_width_px":       round(mean_width, 2),
            "straightness_px":     round(straightness, 2),
            "parallelism_px":      round(parallelism, 2),
            "score_formula":       "score = valid_count / caliper_count",
        },
        "rationale": {
            "direction_rationale": (
                f"{preset.direction.value}: "
                + ("수평 방향 에지 탐색, 폭 / 직진도 측정에 적합"
                   if horizontal
                   else "수직 방향 에지 탐색, 높이 / 수직 직진도 측정에 적합")
            ),
            "count_rationale": (
                f"{preset.caliper_count}개 배치 — "
                f"간격 {spacing}px → 에지 직진도 / 평행도 측정 정밀도 확보"
            ),
            "condition_rationale": (
                f"{preset.condition.value} 조건 — "
                + cond_rationale_map.get(preset.condition, "")
            ),
        },
        "library_mapping": _build_library_mapping(preset),
        "warnings":        warnings,
    }


def _generate_presets(
    h: int,
    w: int,
    polarity: CaliperPolarity,
) -> list[LinearCaliperPreset]:
    """
    Generate three LinearCaliperPreset objects for evaluation.

    Candidates:
      0 — count=6,  RIGHTWARD/DOWNWARD, FIRST  (width measurement focus)
      1 — count=10, same axis,          BEST   (straightness measurement focus)
      2 — count=8,  opposite direction, BEST   (parallelism measurement focus)

    The axis (horizontal / vertical) is chosen based on image aspect ratio:
    wider images use horizontal calipers; taller images use vertical.

    Args:
        h, w:     Image dimensions.
        polarity: Edge polarity inferred from image statistics.

    Returns:
        List of three LinearCaliperPreset objects.
    """
    horizontal = w >= h
    search_len = max(20, min(w, h) // 4)
    proj_len   = max(5,  min(w, h) // 20)

    if horizontal:
        d_primary   = LinearCaliperDirection.RIGHTWARD
        d_secondary = LinearCaliperDirection.LEFTWARD
    else:
        d_primary   = LinearCaliperDirection.DOWNWARD
        d_secondary = LinearCaliperDirection.UPWARD

    return [
        LinearCaliperPreset(
            caliper_count=6,
            direction=d_primary,
            condition=CaliperCondition.FIRST,
            polarity=polarity,
            search_length=search_len,
            projection_length=proj_len,
        ),
        LinearCaliperPreset(
            caliper_count=10,
            direction=d_primary,
            condition=CaliperCondition.BEST,
            polarity=polarity,
            search_length=search_len,
            projection_length=proj_len,
        ),
        LinearCaliperPreset(
            caliper_count=8,
            direction=d_secondary,
            condition=CaliperCondition.BEST,
            polarity=polarity,
            search_length=search_len,
            projection_length=proj_len,
        ),
    ]


# ─── Engine ───────────────────────────────────────────────────────────────────

class LinearCaliperInspectionEngine:
    """
    Linear-caliper-based inspection engine.

    Places N equally-spaced calipers in a horizontal or vertical linear array,
    detects opposing edges via 1D Sobel gradient profiles, computes width /
    straightness / parallelism metrics, rejects 3σ outliers, and returns three
    ranked InspectionCandidate objects with 4-section design documents and
    library-mapping tables.

    CPU-only — NumPy and OpenCV only.

    Args:
        params: Optional dict that overrides the auto-generated primary
                candidate.  Recognised keys (all optional):
                  caliper_count (int, default 8)
                  direction (str: "LEFTWARD"/"RIGHTWARD"/"UPWARD"/"DOWNWARD")
                  condition (str: "FIRST"/"BEST"/"LAST"/"ALL", default "BEST")
                  polarity (str: "DARKER"/"BRIGHTER")
                  search_length (int)
                  projection_length (int)
                  threshold_factor (float, default 1.5)
    """

    def __init__(self, params: dict | None = None) -> None:
        """
        Initialise the engine with optional parameter overrides.

        Args:
            params: Parameter dict for a custom primary candidate.
                    ``None`` or ``{}`` uses fully auto-detected presets.
        """
        self.params: dict = params if params is not None else {}
        self._last_results: list[InspectionCandidate] = []

    def get_strategy_name(self) -> str:
        """Return the human-readable strategy name."""
        return "LinearCaliper"

    def run(
        self,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray] | None = None,
        roi: Optional[ROIConfig] = None,
        purpose: Optional[InspectionPurpose] = None,
    ) -> list[InspectionCandidate]:
        """
        Generate and evaluate linear-caliper inspection candidates.

        Args:
            ok_images: Non-empty list of OK (pass) reference images.
            ng_images: Optional list of NG (fail) images.
            roi:       Optional ROI crop applied before processing.
            purpose:   Optional inspection-purpose metadata (informational).

        Returns:
            List of InspectionCandidate sorted by score descending.

        Raises:
            ValueError: If ok_images is empty.
        """
        if not ok_images:
            raise ValueError("At least one OK image is required")

        if ng_images is None:
            ng_images = []

        ref_cropped = _crop_roi(ok_images[0], roi)
        ref_gray    = _to_gray(ref_cropped)
        h, w        = ref_gray.shape[:2]

        mean_gray = float(np.mean(ref_gray))
        std_gray  = float(np.std(ref_gray))
        polarity  = (CaliperPolarity.BRIGHTER if mean_gray > 100
                     else CaliperPolarity.DARKER)

        presets = _generate_presets(h, w, polarity)

        results: list[InspectionCandidate] = []

        for idx, preset in enumerate(presets):
            try:
                candidate = self._build_candidate(
                    candidate_id=f"linear_caliper_{idx}",
                    preset=preset,
                    ok_images=ok_images,
                    ng_images=ng_images,
                    roi=roi,
                    mean_gray=mean_gray,
                    std_gray=std_gray,
                )
                results.append(candidate)
                logger.info(
                    "Candidate linear_caliper_%d: score=%.3f", idx, candidate.score
                )
            except Exception as exc:
                logger.error("Candidate %d failed: %s — skipping", idx, exc)
                continue

        results.sort(key=lambda c: c.score, reverse=True)
        self._last_results = results
        return results

    def inspect(
        self,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray] | None = None,
        roi: Optional[ROIConfig] = None,
        purpose: Optional[InspectionPurpose] = None,
    ) -> InspectionResult:
        """
        Run the engine and return a structured InspectionResult.

        Wraps :meth:`run` so that callers receive a single object with
        ``success``, ``candidates``, ``best_candidate``, ``error_message``,
        and ``overlay_image`` attributes.

        Args:
            ok_images: Non-empty list of OK reference images.
            ng_images: Optional NG images.
            roi:       Optional ROI crop.
            purpose:   Optional inspection-purpose metadata.

        Returns:
            InspectionResult with success=True and all candidate data on
            success; success=False and error_message populated on failure.
        """
        try:
            candidates = self.run(
                ok_images=ok_images,
                ng_images=ng_images,
                roi=roi,
                purpose=purpose,
            )
            best = candidates[0] if candidates else None

            # Build overlay on the first OK image using the best candidate's
            # measurement data (re-run cheaply on the reference image).
            overlay: Optional[np.ndarray] = None
            if best is not None and ok_images:
                ref_gray = _to_gray(_crop_roi(ok_images[0], roi))
                preset_dict = best.params
                # Reconstruct the direction enum from the stored string value
                dir_val = preset_dict.get("direction", "Rightward")
                direction = LinearCaliperDirection(dir_val)
                cond_val = preset_dict.get("condition", "Best")
                condition = CaliperCondition(cond_val)
                pol_val  = preset_dict.get("polarity", "BrighterThanBackground")
                polarity = CaliperPolarity(pol_val)
                preset = LinearCaliperPreset(
                    caliper_count=int(preset_dict.get("caliper_count", 8)),
                    direction=direction,
                    condition=condition,
                    polarity=polarity,
                    search_length=int(preset_dict.get("search_length", 20)),
                    projection_length=int(preset_dict.get("projection_length", 5)),
                    threshold_factor=float(preset_dict.get("threshold_factor", 1.5)),
                )
                m = _compute_measurements(ref_gray, preset)
                src = (ok_images[0] if ok_images[0].ndim == 3
                       else cv2.cvtColor(ok_images[0], cv2.COLOR_GRAY2BGR))
                overlay = _draw_overlay(src, m, direction)

            return InspectionResult(
                success=bool(candidates),
                strategy_name=self.get_strategy_name(),
                score=best.score if best else 0.0,
                is_ok=bool(candidates),
                failure_reason=None,
                overlay_image=overlay,
                candidates=candidates,
                best_candidate=best,
                error_message=None,
            )
        except Exception as exc:
            logger.error("inspect() failed: %s", exc)
            return InspectionResult(
                success=False,
                strategy_name=self.get_strategy_name(),
                score=0.0,
                is_ok=False,
                failure_reason=str(exc),
                overlay_image=None,
                candidates=[],
                best_candidate=None,
                error_message=str(exc),
            )

    def generate_design_document(self) -> dict:
        """
        Return the 4-section design document of the best-scoring candidate
        from the most recent :meth:`run` / :meth:`inspect` call.

        The document has keys: placement, caliper_params, result_calculation,
        rationale (plus library_mapping and warnings).

        Returns:
            Dict with the 4-section structure, or an empty dict if the engine
            has not been run yet.
        """
        if self._last_results:
            return self._last_results[0].design_doc
        return {}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _compute_measurements(
        self,
        gray: np.ndarray,
        preset: LinearCaliperPreset,
    ) -> dict:
        """
        Run the full caliper pipeline on one grayscale image.

        Delegates to the module-level :func:`_compute_measurements`.

        Args:
            gray:   Single-channel image (already ROI-cropped).
            preset: Parameter preset.

        Returns:
            Measurement dict (see :func:`_compute_measurements`).
        """
        return _compute_measurements(gray, preset)

    def _draw_overlay(
        self,
        image: np.ndarray,
        measurements: dict,
        direction: LinearCaliperDirection,
    ) -> np.ndarray:
        """
        Draw edge points and fitted lines on *image*.

        Delegates to the module-level :func:`_draw_overlay`.

        Args:
            image:        Source image (BGR or grayscale).
            measurements: Output of :func:`_compute_measurements`.
            direction:    Search direction.

        Returns:
            Annotated BGR ndarray.
        """
        return _draw_overlay(image, measurements, direction)

    def _build_candidate(
        self,
        candidate_id: str,
        preset: LinearCaliperPreset,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        roi: Optional[ROIConfig],
        mean_gray: float,
        std_gray: float,
    ) -> InspectionCandidate:
        """
        Build one InspectionCandidate for a given preset.

        OK pass-rate: fraction of OK images whose mean width is within ±5 %
        of the reference width measured on the first OK image.

        Args:
            candidate_id: Unique string identifier.
            preset:       LinearCaliperPreset to evaluate.
            ok_images:    OK reference images.
            ng_images:    NG images.
            roi:          Optional crop region.
            mean_gray:    Mean grey value of the reference image.
            std_gray:     Std of grey values of the reference image.

        Returns:
            Populated InspectionCandidate.
        """
        ref_gray = _to_gray(_crop_roi(ok_images[0], roi))
        h_ref, w_ref = ref_gray.shape[:2]

        ref_m    = _compute_measurements(ref_gray, preset)
        ref_width = ref_m["mean_width"]
        tol       = max(3.0, ref_width * 0.05)

        def _is_ok_img(img: np.ndarray) -> bool:
            """Return True if img width is within tolerance of ref_width."""
            gray = _to_gray(_crop_roi(img, roi))
            m = _compute_measurements(gray, preset)
            if m["valid_count"] < 1:
                return False
            return abs(m["mean_width"] - ref_width) <= tol

        ok_pass        = sum(1 for img in ok_images if _is_ok_img(img))
        ng_fail        = sum(1 for img in ng_images if not _is_ok_img(img))
        ok_pass_rate   = ok_pass  / len(ok_images) if ok_images else 0.0
        ng_detect_rate = ng_fail  / len(ng_images) if ng_images else 0.0
        score          = ok_pass_rate * 0.5 + ng_detect_rate * 0.5

        design_doc      = _build_design_doc(preset, ref_m, h_ref, w_ref)
        library_mapping = _build_library_mapping(preset)

        src_for_overlay = (ok_images[0] if ok_images[0].ndim == 3
                           else cv2.cvtColor(ok_images[0], cv2.COLOR_GRAY2BGR))
        overlay_img = _draw_overlay(src_for_overlay, ref_m, preset.direction)

        valid_count = ref_m["valid_count"]
        rationale = (
            f"Linear Caliper — {preset.caliper_count}개, "
            f"{preset.direction.value}, {preset.condition.value}. "
            f"유효 포인트 {valid_count}/{preset.caliper_count}. "
            f"평균 폭 {ref_width:.1f}px, 직진도 {ref_m['straightness']:.1f}px, "
            f"평행도 {ref_m['parallelism']:.1f}px. "
            f"Score={score:.3f} (OK={ok_pass_rate:.1%}, NG={ng_detect_rate:.1%})."
        )

        return InspectionCandidate(
            candidate_id=candidate_id,
            method="linear_caliper",
            params=preset.to_dict(),
            design_doc=design_doc,
            library_mapping=library_mapping,
            ok_pass_rate=ok_pass_rate,
            ng_detect_rate=ng_detect_rate,
            score=score,
            rationale=rationale,
            overlay_image_path=None,
        )
