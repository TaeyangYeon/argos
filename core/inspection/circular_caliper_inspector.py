"""
Circular Caliper Inspection Engine (Argos Step 35).

Places N calipers evenly around a reference circle, extracts radial Sobel
gradient profiles, detects edges, fits a circle via Least-Squares, rejects
outliers by 3σ, and returns three ranked candidates with 4-section design
documents and library-mapping tables.

CPU-only — NumPy and OpenCV only. No scikit-image, no torch.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from core.models import InspectionCandidate, InspectionPurpose, ROIConfig

logger = logging.getLogger("argos.inspection.circular_caliper")


# ─── Enumerations ─────────────────────────────────────────────────────────────

class CaliperCondition(str, Enum):
    """Edge selection condition within the search profile."""
    FIRST = "First"
    BEST  = "Best"
    LAST  = "Last"
    ALL   = "All"


class CaliperPolarity(str, Enum):
    """Expected polarity of the edge transition."""
    DARKER   = "DarkerThanBackground"
    BRIGHTER = "BrighterThanBackground"


class CaliperDirection(str, Enum):
    """Radial search direction for each caliper."""
    INWARD  = "Inward"
    OUTWARD = "Outward"


# ─── Candidate descriptor ─────────────────────────────────────────────────────

@dataclass
class CaliperCandidate:
    """Parameter preset for one circular-caliper candidate."""
    caliper_count: int
    direction: CaliperDirection
    condition: CaliperCondition
    polarity: CaliperPolarity
    search_length: int
    projection_length: int
    search_radius: int
    start_angle_deg: float = 0.0

    def to_dict(self) -> dict:
        """Serialise to a plain JSON-compatible dict."""
        return {
            "caliper_count":    self.caliper_count,
            "direction":        self.direction.value,
            "condition":        self.condition.value,
            "polarity":         self.polarity.value,
            "search_length":    self.search_length,
            "projection_length": self.projection_length,
            "search_radius":    self.search_radius,
            "start_angle_deg":  self.start_angle_deg,
        }


# ─── Library name mapping ─────────────────────────────────────────────────────

def _build_library_mapping(p: CaliperCandidate) -> dict:
    """
    Return a Keyence / Cognex / Halcon / MIL parameter-name translation table.

    Args:
        p: CaliperCandidate whose parameters are used to fill concrete values.

    Returns:
        Nested dict keyed by library name.
    """
    dir_map = {
        CaliperDirection.INWARD:  ("내측 방향", "Inward",  "'inner'",  "M_INWARD"),
        CaliperDirection.OUTWARD: ("외측 방향", "Outward", "'outer'",  "M_OUTWARD"),
    }
    cond_map = {
        CaliperCondition.FIRST: ("첫 번째 에지", "First", "'first'", "M_FIRST_CONTRAST"),
        CaliperCondition.BEST:  ("최적 에지",    "Best",  "'best'",  "M_BEST_CONTRAST"),
        CaliperCondition.LAST:  ("마지막 에지",  "Last",  "'last'",  "M_LAST_CONTRAST"),
        CaliperCondition.ALL:   ("모든 에지",    "All",   "'all'",   "M_ALL_CONTRAST"),
    }
    kd, cod, hd, md = dir_map[p.direction]
    kc, coc, hc, mc = cond_map[p.condition]
    return {
        "concept_table": {
            "Search Length":     {"Keyence": f"탐색 폭 = {p.search_length}px",
                                  "Cognex":  f"SearchLength = {p.search_length}",
                                  "Halcon":  f"SearchExtent = {p.search_length}",
                                  "MIL":     f"M_SEARCH_LENGTH = {p.search_length}"},
            "Projection Length": {"Keyence": f"투영 길이 = {p.projection_length}px",
                                  "Cognex":  f"ProjectionLength = {p.projection_length}",
                                  "Halcon":  f"ProfileLength = {p.projection_length}",
                                  "MIL":     f"M_PROJECTION_LENGTH = {p.projection_length}"},
            "Condition":         {"Keyence": kc, "Cognex": coc, "Halcon": hc, "MIL": mc},
            "Direction":         {"Keyence": kd, "Cognex": cod, "Halcon": hd, "MIL": md},
            "Caliper Count":     {"Keyence": f"Caliper 수 = {p.caliper_count}",
                                  "Cognex":  f"NumCalipers = {p.caliper_count}",
                                  "Halcon":  f"NumMeasureObjects = {p.caliper_count}",
                                  "MIL":     f"M_CALIPER_COUNT = {p.caliper_count}"},
        }
    }


# ─── Helper functions ──────────────────────────────────────────────────────────

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


def _estimate_circle(gray: np.ndarray) -> tuple[float, float, float]:
    """
    Estimate the dominant circle in *gray* using HoughCircles.

    Returns:
        (cx, cy, radius) in pixels. Falls back to image centre with
        radius = min(h, w) / 3 when no circle is detected.
    """
    h, w = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT,
        dp=1.2, minDist=min(h, w) // 4,
        param1=80, param2=30,
        minRadius=max(10, min(h, w) // 8),
        maxRadius=min(h, w) // 2,
    )
    if circles is not None:
        c = circles[0, 0]
        return float(c[0]), float(c[1]), float(c[2])
    return float(w / 2), float(h / 2), float(min(h, w) / 3)


# ─── Core numerical routines ───────────────────────────────────────────────────

def _extract_edge_point(
    gray: np.ndarray,
    cx: float,
    cy: float,
    angle_deg: float,
    direction: CaliperDirection,
    search_radius: int,
    search_length: int,
    projection_length: int,
    condition: CaliperCondition,
    polarity: CaliperPolarity,
) -> tuple[float, float] | None:
    """
    Extract a single edge point along the radial profile at *angle_deg*.

    The profile is sampled as a line segment of length *search_length* starting
    at *search_radius* pixels from (cx, cy) in the specified *direction*.
    A Sobel derivative is computed along the profile; the selected edge peak is
    returned as a (px, py) coordinate in image space.

    Args:
        gray:             Single-channel image.
        cx, cy:           Reference circle centre.
        angle_deg:        Caliper angle in degrees (0 = right, CCW positive).
        direction:        INWARD searches from outside toward centre; OUTWARD vice versa.
        search_radius:    Distance from centre to start the search profile (px).
        search_length:    Length of the search profile (px).
        projection_length: Half-width of the profile for gradient averaging (px).
        condition:        FIRST / BEST / LAST / ALL — which edge peak to pick.
        polarity:         Expected brightness transition.

    Returns:
        (px, py) of the detected edge point, or None if no edge found.
    """
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    # Unit vector along the profile (inward = toward centre)
    if direction == CaliperDirection.INWARD:
        dx, dy = -cos_a, -sin_a
        start_x = cx + search_radius * cos_a
        start_y = cy + search_radius * sin_a
    else:
        dx, dy = cos_a, sin_a
        start_x = cx - search_radius * cos_a
        start_y = cy - search_radius * sin_a

    # Perpendicular unit vector for projection averaging
    perp_x, perp_y = -sin_a, cos_a

    h, w = gray.shape[:2]
    n_proj = max(1, projection_length)
    profile = np.zeros(search_length, dtype=np.float32)

    for i in range(search_length):
        px0 = start_x + i * dx
        py0 = start_y + i * dy
        acc, count = 0.0, 0
        for j in range(-n_proj // 2, n_proj // 2 + 1):
            px_s = int(round(px0 + j * perp_x))
            py_s = int(round(py0 + j * perp_y))
            if 0 <= px_s < w and 0 <= py_s < h:
                acc += float(gray[py_s, px_s])
                count += 1
        profile[i] = acc / count if count > 0 else 0.0

    # Sobel derivative along the profile
    if len(profile) < 3:
        return None
    kernel = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
    gradient = np.convolve(profile, kernel, mode="same")

    # Polarity flip
    if polarity == CaliperPolarity.DARKER:
        gradient = -gradient

    if np.max(gradient) <= 0:
        return None

    # Edge selection
    if condition == CaliperCondition.FIRST:
        peaks = np.where(gradient > 0)[0]
        idx = int(peaks[0]) if len(peaks) > 0 else None
    elif condition == CaliperCondition.LAST:
        peaks = np.where(gradient > 0)[0]
        idx = int(peaks[-1]) if len(peaks) > 0 else None
    elif condition == CaliperCondition.BEST:
        idx = int(np.argmax(gradient))
    else:  # ALL — use strongest
        idx = int(np.argmax(gradient))

    if idx is None:
        return None

    ex = start_x + idx * dx
    ey = start_y + idx * dy
    if not (0 <= ex < w and 0 <= ey < h):
        return None
    return (ex, ey)


def _fit_circle_lsq(
    points: list[tuple[float, float]],
) -> tuple[float, float, float]:
    """
    Fit a circle to *points* using algebraic Least-Squares (Coope method).

    Solves the linear system  2xi*cx + 2yi*cy + d = xi²+yi²
    where d = cx²+cy²−r².

    Args:
        points: List of (x, y) edge coordinates.

    Returns:
        (cx, cy, radius) of the best-fit circle.

    Raises:
        ValueError: If fewer than 3 points are supplied.
    """
    if len(points) < 3:
        raise ValueError("At least 3 points required for circle fitting")

    pts = np.asarray(points, dtype=np.float64)
    x, y = pts[:, 0], pts[:, 1]
    A = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    result, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = result[0], result[1]
    d = result[2]
    r2 = d + cx ** 2 + cy ** 2
    radius = math.sqrt(max(r2, 0.0))
    return float(cx), float(cy), float(radius)


def _reject_outliers(
    points: list[tuple[float, float]],
    cx: float,
    cy: float,
    radius: float,
) -> list[tuple[float, float]]:
    """
    Remove points whose radial deviation from the fitted circle exceeds 3σ.

    Args:
        points: Raw edge points.
        cx, cy: Fitted circle centre.
        radius: Fitted circle radius.

    Returns:
        Filtered list of inlier points.
    """
    if not points:
        return []
    deviations = np.array([
        abs(math.hypot(p[0] - cx, p[1] - cy) - radius)
        for p in points
    ], dtype=np.float64)
    sigma = float(np.std(deviations))
    threshold = 3.0 * sigma
    return [p for p, d in zip(points, deviations) if d <= threshold + 1e-9]


def _draw_overlay(
    image: np.ndarray,
    points: list[tuple[float, float]],
    cx: float,
    cy: float,
    radius: float,
) -> np.ndarray:
    """
    Draw detected edge points and fitted circle on a copy of *image*.

    Args:
        image:  Source image (BGR or grayscale).
        points: Inlier edge points to draw.
        cx, cy: Fitted circle centre.
        radius: Fitted circle radius.

    Returns:
        BGR uint8 ndarray with annotations.
    """
    overlay = image.copy()
    if overlay.ndim == 2:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

    # Fitted circle
    cv2.circle(overlay, (int(round(cx)), int(round(cy))), int(round(radius)),
               (0, 255, 0), 2)
    # Centre cross
    cv2.drawMarker(overlay, (int(round(cx)), int(round(cy))),
                   (0, 255, 0), cv2.MARKER_CROSS, 12, 2)

    # Edge points
    for px, py in points:
        cv2.circle(overlay, (int(round(px)), int(round(py))), 3,
                   (0, 0, 255), -1)

    return overlay


def _build_design_doc(
    candidate: CaliperCandidate,
    result_stats: dict,
) -> dict:
    """
    Build the mandatory 4-section design document for one candidate.

    Args:
        candidate:    The caliper preset used.
        result_stats: Runtime stats (valid_count, fitted_radius, …).

    Returns:
        JSON-serialisable dict with keys: placement_structure, individual_caliper_params,
        result_calculation, selection_rationale, library_mapping, warnings.
    """
    angle_interval = round(360.0 / candidate.caliper_count, 2)
    valid_count: int = result_stats.get("valid_count", 0)
    fitted_radius: float = result_stats.get("fitted_radius", 0.0)
    hough_radius: float  = result_stats.get("hough_radius", 0.0)
    mean_gray: float     = result_stats.get("mean_gray", 0.0)
    std_gray: float      = result_stats.get("std_gray", 0.0)

    warnings: list[str] = []
    if valid_count < 8:
        warnings.append(
            f"유효 Caliper 수 부족 ({valid_count}개 < 8개) — 신뢰도 낮음"
        )

    doc = {
        "placement_structure": {
            "arrangement":       "원형 등간격 배치",
            "caliper_count":     candidate.caliper_count,
            "angle_interval_deg": angle_interval,
            "start_angle_deg":   candidate.start_angle_deg,
            "search_direction":  candidate.direction.value,
            "search_radius_px":  candidate.search_radius,
        },
        "individual_caliper_params": {
            "search_length_px":    candidate.search_length,
            "projection_length_px": candidate.projection_length,
            "condition":           candidate.condition.value,
            "polarity":            candidate.polarity.value,
            "edge_filter":         "Sobel 1D along radial direction",
        },
        "result_calculation": {
            "method":              "LSQ Circle Fit (algebraic, Coope)",
            "outlier_rejection":   "3σ radial deviation removal + refit",
            "confidence_condition": "valid_caliper_count >= 8",
            "valid_caliper_count": valid_count,
            "fitted_radius_px":    round(fitted_radius, 2),
            "hough_ref_radius_px": round(hough_radius, 2),
            "score_formula":       "score = valid_count / caliper_count",
        },
        "selection_rationale": {
            "image_mean_gray":  round(mean_gray, 1),
            "image_std_gray":   round(std_gray, 1),
            "caliper_count_rationale": (
                f"{candidate.caliper_count}개 배치 — "
                f"각도 간격 {angle_interval}° → 원형도 측정 정밀도 확보"
            ),
            "direction_rationale": (
                f"{candidate.direction.value}: "
                + ("원 외부→내부 탐색, 배경 대비 밝은 원 가장자리 검출에 적합"
                   if candidate.direction == CaliperDirection.INWARD
                   else "원 중심→외부 탐색, 어두운 배경 기준 에지 검출에 적합")
            ),
            "condition_rationale": (
                f"{candidate.condition.value} 조건 — "
                + {
                    CaliperCondition.FIRST: "탐색 시작점에서 첫 에지 선택, 노이즈 적은 환경에 유리",
                    CaliperCondition.BEST:  "최대 그래디언트 에지 선택, 대비 좋은 환경에서 가장 안정적",
                    CaliperCondition.LAST:  "마지막 에지 선택, 이중 엣지 환경에서 외곽 선택 시 사용",
                    CaliperCondition.ALL:   "모든 에지 평균, 다층 구조 이미지에 적합",
                }[candidate.condition]
            ),
        },
        "library_mapping": _build_library_mapping(candidate),
        "warnings": warnings,
    }
    return doc


# ─── Three-candidate presets ───────────────────────────────────────────────────

def _generate_candidates(
    hough_radius: int,
    polarity: CaliperPolarity,
) -> list[CaliperCandidate]:
    """
    Generate three CaliperCandidate presets for evaluation.

    Varying caliper_count (8 / 12 / 16) and direction (Inward / Inward / Outward).

    Args:
        hough_radius: Reference radius detected from the image (px).
        polarity:     Edge polarity derived from image statistics.

    Returns:
        List of three CaliperCandidate objects.
    """
    base_search  = max(20, hough_radius // 4)
    base_proj    = max(5,  hough_radius // 10)
    # INWARD: start outside the circle (search_radius > hough_radius)
    inward_start = hough_radius + base_search // 2
    # OUTWARD: start inside the circle (search_radius < hough_radius)
    outward_start = max(5, hough_radius - base_search)

    return [
        CaliperCandidate(
            caliper_count=8,
            direction=CaliperDirection.INWARD,
            condition=CaliperCondition.BEST,
            polarity=polarity,
            search_length=base_search,
            projection_length=base_proj,
            search_radius=inward_start,
            start_angle_deg=0.0,
        ),
        CaliperCandidate(
            caliper_count=12,
            direction=CaliperDirection.INWARD,
            condition=CaliperCondition.FIRST,
            polarity=polarity,
            search_length=base_search,
            projection_length=base_proj,
            search_radius=inward_start,
            start_angle_deg=0.0,
        ),
        CaliperCandidate(
            caliper_count=16,
            direction=CaliperDirection.OUTWARD,
            condition=CaliperCondition.BEST,
            polarity=polarity,
            search_length=base_search,
            projection_length=base_proj,
            search_radius=outward_start,
            start_angle_deg=0.0,
        ),
    ]


# ─── Engine ───────────────────────────────────────────────────────────────────

class CircularCaliperInspectionEngine:
    """
    Circular-caliper-based inspection engine.

    Places N equally-spaced calipers around a reference circle, detects edges
    via radial Sobel gradient profiles, fits a circle by algebraic Least-Squares,
    and rejects outliers by 3σ.  Returns three ranked InspectionCandidate objects
    with 4-section design documents and library-mapping tables.

    CPU-only — NumPy and OpenCV only.

    Args:
        params: Optional parameter dict that overrides the auto-generated primary
                candidate.  Recognised keys (all optional with defaults):
                  caliper_count (int, default 12)
                  start_angle_deg (float, default 0.0)
                  search_radius (int, default auto)
                  search_length (int, default auto)
                  projection_length (int, default auto)
                  condition (str: "FIRST"/"BEST"/"LAST"/"ALL", default "BEST")
                  polarity (str: "DARKER"/"BRIGHTER", default "BRIGHTER")
                  direction (str: "INWARD"/"OUTWARD", default "INWARD")
    """

    def __init__(self, params: dict | None = None) -> None:
        """
        Initialise the engine, optionally pre-loading a parameter dict.

        Args:
            params: Parameter dict for the custom primary candidate.
                    Passing ``None`` or ``{}`` uses fully auto-detected presets.
        """
        self.params: dict = params if params is not None else {}

    def _params_to_candidate(
        self,
        params: dict,
        hough_radius: int,
        image_polarity: CaliperPolarity,
    ) -> CaliperCandidate:
        """
        Convert a user-supplied params dict into a ``CaliperCandidate``.

        Missing keys are filled with safe defaults derived from the
        auto-detected *hough_radius* and *image_polarity*.

        Args:
            params:         User-supplied parameter dict.
            hough_radius:   Auto-detected circle radius (px).
            image_polarity: Polarity inferred from image statistics.

        Returns:
            A fully-populated ``CaliperCandidate``.
        """
        base_search = max(20, hough_radius // 4)
        base_proj   = max(5,  hough_radius // 10)

        cond_map = {
            "FIRST": CaliperCondition.FIRST,
            "BEST":  CaliperCondition.BEST,
            "LAST":  CaliperCondition.LAST,
            "ALL":   CaliperCondition.ALL,
        }
        pol_map = {
            "DARKER":    CaliperPolarity.DARKER,
            "BRIGHTER":  CaliperPolarity.BRIGHTER,
        }
        dir_map = {
            "INWARD":  CaliperDirection.INWARD,
            "OUTWARD": CaliperDirection.OUTWARD,
        }

        condition  = cond_map.get(str(params.get("condition", "BEST")).upper(),
                                  CaliperCondition.BEST)
        polarity   = pol_map.get(str(params.get("polarity", "")).upper(),
                                 image_polarity)
        direction  = dir_map.get(str(params.get("direction", "INWARD")).upper(),
                                 CaliperDirection.INWARD)

        return CaliperCandidate(
            caliper_count    = int(params.get("caliper_count",    12)),
            start_angle_deg  = float(params.get("start_angle_deg", 0.0)),
            search_radius    = int(params.get("search_radius",
                                              hough_radius + base_search // 2)),
            search_length    = int(params.get("search_length",    base_search)),
            projection_length = int(params.get("projection_length", base_proj)),
            condition        = condition,
            polarity         = polarity,
            direction        = direction,
        )

    def get_strategy_name(self) -> str:
        """Return the human-readable strategy name."""
        return "CircularCaliper"

    def run(
        self,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray] | None = None,
        roi: Optional[ROIConfig] = None,
        purpose: Optional[InspectionPurpose] = None,
    ) -> list[InspectionCandidate]:
        """
        Generate and evaluate circular-caliper inspection candidates.

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

        # Use first OK image to estimate circle geometry and image statistics
        ref_gray = _to_gray(_crop_roi(ok_images[0], roi))
        mean_gray = float(np.mean(ref_gray))
        std_gray  = float(np.std(ref_gray))
        cx0, cy0, r0 = _estimate_circle(ref_gray)
        polarity = (CaliperPolarity.BRIGHTER if mean_gray > 100
                    else CaliperPolarity.DARKER)

        preset_candidates = _generate_candidates(int(round(r0)), polarity)

        # If the engine was constructed with explicit params, prepend a custom
        # candidate built from those params so it is always evaluated first.
        if self.params:
            custom = self._params_to_candidate(self.params, int(round(r0)), polarity)
            preset_candidates = [custom] + preset_candidates

        results: list[InspectionCandidate] = []

        for idx, preset in enumerate(preset_candidates):
            try:
                candidate = self._build_candidate(
                    candidate_id=f"circular_caliper_{idx}",
                    preset=preset,
                    ok_images=ok_images,
                    ng_images=ng_images,
                    roi=roi,
                    cx0=cx0, cy0=cy0, r0=r0,
                    mean_gray=mean_gray,
                    std_gray=std_gray,
                )
                results.append(candidate)
                logger.info(
                    "Candidate circular_caliper_%d: score=%.3f", idx, candidate.score
                )
            except Exception as exc:
                logger.error("Candidate %d failed: %s — skipping", idx, exc)
                continue

        results.sort(key=lambda c: c.score, reverse=True)
        return results

    # ── Private helpers ───────────────────────────────────────────────────────

    def _place_calipers(
        self,
        caliper_count: int,
        start_angle_deg: float,
    ) -> list[dict]:
        """
        Compute the angle (degrees) for each caliper placement.

        Args:
            caliper_count:   Total number of calipers to place.
            start_angle_deg: Starting angle in degrees.

        Returns:
            List of dicts with key 'angle_deg'.
        """
        step = 360.0 / caliper_count
        return [
            {"angle_deg": (start_angle_deg + k * step) % 360}
            for k in range(caliper_count)
        ]

    def _extract_edge_point(
        self,
        image: np.ndarray,
        cx: float,
        cy: float,
        angle_deg: float,
        direction: CaliperDirection,
        search_radius: int,
        search_length: int,
        projection_length: int,
        condition: CaliperCondition,
        polarity: CaliperPolarity,
    ) -> tuple[float, float] | None:
        """
        Delegate to the module-level edge extraction function.

        Returns:
            (px, py) or None if no edge detected.
        """
        return _extract_edge_point(
            image, cx, cy, angle_deg, direction,
            search_radius, search_length, projection_length,
            condition, polarity,
        )

    def _fit_circle_lsq(
        self,
        points: list[tuple[float, float]],
    ) -> tuple[float, float, float]:
        """
        Fit circle to *points* via Least-Squares (delegates to module function).

        Returns:
            (cx, cy, radius).
        """
        return _fit_circle_lsq(points)

    def _reject_outliers(
        self,
        points: list[tuple[float, float]],
        cx: float,
        cy: float,
        radius: float,
    ) -> list[tuple[float, float]]:
        """
        Remove 3σ outliers from *points* (delegates to module function).

        Returns:
            Filtered inlier list.
        """
        return _reject_outliers(points, cx, cy, radius)

    def _generate_candidates(
        self,
        hough_radius: int,
        polarity: CaliperPolarity,
    ) -> list[CaliperCandidate]:
        """
        Generate three parameter presets (delegates to module function).

        Returns:
            List of three CaliperCandidate objects.
        """
        return _generate_candidates(hough_radius, polarity)

    def _build_design_doc(
        self,
        candidate: CaliperCandidate,
        result_stats: dict,
    ) -> dict:
        """
        Build the 4-section design document (delegates to module function).

        Returns:
            JSON-serialisable dict.
        """
        return _build_design_doc(candidate, result_stats)

    def _draw_overlay(
        self,
        image: np.ndarray,
        points: list[tuple[float, float]],
        cx: float,
        cy: float,
        radius: float,
    ) -> np.ndarray:
        """
        Draw edge points and fitted circle (delegates to module function).

        Returns:
            Annotated BGR ndarray.
        """
        return _draw_overlay(image, points, cx, cy, radius)

    def _run_on_image(
        self,
        gray: np.ndarray,
        preset: CaliperCandidate,
        cx0: float,
        cy0: float,
    ) -> tuple[list[tuple[float, float]], float, float, float]:
        """
        Run the full caliper pipeline on one grayscale image.

        Steps: place calipers → extract edges → fit circle → reject outliers → refit.

        Args:
            gray:       Grayscale image.
            preset:     CaliperCandidate describing the parameters.
            cx0, cy0:   Initial circle centre estimate.

        Returns:
            (inlier_points, fitted_cx, fitted_cy, fitted_radius)
        """
        placements = self._place_calipers(preset.caliper_count, preset.start_angle_deg)
        raw_points: list[tuple[float, float]] = []
        for pl in placements:
            pt = self._extract_edge_point(
                gray, cx0, cy0, pl["angle_deg"],
                preset.direction, preset.search_radius, preset.search_length,
                preset.projection_length, preset.condition, preset.polarity,
            )
            if pt is not None:
                raw_points.append(pt)

        if len(raw_points) < 3:
            return raw_points, cx0, cy0, float(preset.search_radius)

        cx, cy, r = self._fit_circle_lsq(raw_points)
        inliers = self._reject_outliers(raw_points, cx, cy, r)

        if len(inliers) >= 3:
            cx, cy, r = self._fit_circle_lsq(inliers)
        else:
            inliers = raw_points

        return inliers, cx, cy, r

    def _build_candidate(
        self,
        candidate_id: str,
        preset: CaliperCandidate,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        roi: Optional[ROIConfig],
        cx0: float,
        cy0: float,
        r0: float,
        mean_gray: float,
        std_gray: float,
    ) -> InspectionCandidate:
        """
        Build one InspectionCandidate for a given parameter preset.

        Computes OK pass-rate and NG detect-rate by comparing the fitted-circle
        radius deviation against a tolerance of ±5 % of the reference radius.

        Args:
            candidate_id: Unique string ID for this candidate.
            preset:       CaliperCandidate parameter set.
            ok_images:    OK reference images.
            ng_images:    NG images.
            roi:          Optional crop region.
            cx0, cy0:     Reference circle centre (px).
            r0:           Reference circle radius (px).
            mean_gray:    Mean grey value of the reference image.
            std_gray:     Std of grey values of the reference image.

        Returns:
            Populated InspectionCandidate.
        """
        tol = max(3.0, r0 * 0.05)  # ±5 % tolerance

        def _is_ok(img: np.ndarray) -> bool:
            gray = _to_gray(_crop_roi(img, roi))
            pts, cx, cy, r = self._run_on_image(gray, preset, cx0, cy0)
            return abs(r - r0) <= tol

        ok_pass  = sum(1 for img in ok_images if _is_ok(img))
        ng_fail  = sum(1 for img in ng_images if not _is_ok(img))

        ok_pass_rate  = ok_pass  / len(ok_images) if ok_images else 0.0
        ng_detect_rate = ng_fail / len(ng_images) if ng_images else 0.0
        score = ok_pass_rate * 0.5 + ng_detect_rate * 0.5

        # Run on first OK image for design doc stats and overlay
        ref_gray = _to_gray(_crop_roi(ok_images[0], roi))
        inliers, fit_cx, fit_cy, fit_r = self._run_on_image(ref_gray, preset, cx0, cy0)

        result_stats = {
            "valid_count":    len(inliers),
            "fitted_radius":  fit_r,
            "hough_radius":   r0,
            "mean_gray":      mean_gray,
            "std_gray":       std_gray,
        }

        design_doc      = self._build_design_doc(preset, result_stats)
        library_mapping = _build_library_mapping(preset)
        overlay_img     = self._draw_overlay(ok_images[0], inliers, fit_cx, fit_cy, fit_r)

        rationale = (
            f"Circular Caliper — {preset.caliper_count}개, "
            f"{preset.direction.value}, {preset.condition.value}. "
            f"유효 포인트 {len(inliers)}/{preset.caliper_count}. "
            f"피팅 반경 {fit_r:.1f}px (기준 {r0:.1f}px). "
            f"Score={score:.3f} (OK={ok_pass_rate:.1%}, NG={ng_detect_rate:.1%})."
        )

        return InspectionCandidate(
            candidate_id=candidate_id,
            method="circular_caliper",
            params=preset.to_dict(),
            design_doc=design_doc,
            library_mapping=library_mapping,
            ok_pass_rate=ok_pass_rate,
            ng_detect_rate=ng_detect_rate,
            score=score,
            rationale=rationale,
            overlay_image_path=None,  # kept in-memory via overlay_img
        )
