"""
Blob-based Inspection Engine (Argos Step 33).

Analyses OK / NG image sets using connected-component blob detection and
produces three ranked InspectionCandidate objects with four-section design
documents and library-mapping tables.

CPU-only — uses only OpenCV morphological operations and
cv2.connectedComponentsWithStats.  No GPU, no deep learning.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from core.exceptions import InputValidationError
from core.models import InspectionCandidate, InspectionPurpose, ROIConfig

logger = logging.getLogger("argos.inspection.blob")

# ─── Overlay output directory ────────────────────────────────────────────────

_OVERLAY_DIR = Path(tempfile.gettempdir()) / "argos_overlays"

# ─── Library-name mapping template ───────────────────────────────────────────

def _build_library_mapping(params: dict) -> dict:
    """Return a Keyence / Cognex / Halcon / MIL parameter mapping table."""
    area_min = params.get("area_min", 0)
    area_max = params.get("area_max", 999999)
    circ = params.get("circularity_min", 0.0)
    ar = params.get("aspect_ratio_max", 99.0)
    sol = params.get("solidity_min", 0.0)

    return {
        "keyence": {
            "description": "Keyence BlobMeasure / BlobCount tool",
            "area_min": f"Area Filter Min = {area_min} px²",
            "area_max": f"Area Filter Max = {area_max} px²",
            "circularity": f"Circularity >= {circ:.2f}",
            "aspect_ratio": f"Aspect Ratio <= {ar:.2f}",
            "solidity": f"Compactness >= {sol:.2f}",
        },
        "cognex": {
            "description": "CogBlobTool (In-Sight Explorer)",
            "area_min": f"MinBlobArea = {area_min}",
            "area_max": f"MaxBlobArea = {area_max}",
            "circularity": f"MinCircularity = {circ:.3f}",
            "aspect_ratio": f"MaxAspectRatio = {ar:.2f}",
            "solidity": f"MinSolidity = {sol:.3f}",
        },
        "halcon": {
            "description": "select_shape / connection (HALCON HDevelop)",
            "area_min": f"select_shape(Regions, 'area', 'and', {area_min}, {area_max})",
            "circularity": f"select_shape(Regions, 'circularity', 'and', {circ:.3f}, 1.0)",
            "aspect_ratio": f"select_shape(Regions, 'ratio', 'and', 0.0, {ar:.2f})",
            "solidity": f"select_shape(Regions, 'compactness', 'and', {sol:.3f}, 1.0)",
        },
        "mil": {
            "description": "MblobAnalyze / MblobSelect (Matrox MIL)",
            "area_min": f"MblobControl(MilBlob, M_AREA+M_MIN_VALUE, {area_min})",
            "area_max": f"MblobControl(MilBlob, M_AREA+M_MAX_VALUE, {area_max})",
            "circularity": f"MblobControl(MilBlob, M_COMPACTNESS+M_MIN_VALUE, {circ:.3f})",
            "aspect_ratio": f"MblobControl(MilBlob, M_FERET_ELONGATION+M_MAX_VALUE, {ar:.2f})",
        },
    }


# ─── Candidate parameter presets ─────────────────────────────────────────────

_PRESETS: list[dict] = [
    {
        "id_suffix": "A",
        "label": "strict",
        "area_min": 200,
        "area_max": 5000,
        "circularity_min": 0.70,
        "aspect_ratio_max": 2.0,
        "solidity_min": 0.80,
        "morph_kernel": 3,
        "blur_ksize": 3,
    },
    {
        "id_suffix": "B",
        "label": "moderate",
        "area_min": 100,
        "area_max": 20000,
        "circularity_min": 0.40,
        "aspect_ratio_max": 4.0,
        "solidity_min": 0.60,
        "morph_kernel": 5,
        "blur_ksize": 5,
    },
    {
        "id_suffix": "C",
        "label": "loose",
        "area_min": 30,
        "area_max": 80000,
        "circularity_min": 0.10,
        "aspect_ratio_max": 10.0,
        "solidity_min": 0.30,
        "morph_kernel": 7,
        "blur_ksize": 7,
    },
]


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _crop_roi(image: np.ndarray, roi: Optional[ROIConfig]) -> np.ndarray:
    if roi is None:
        return image
    y2 = roi.y + roi.height
    x2 = roi.x + roi.width
    return image[roi.y:y2, roi.x:x2]


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _binarize(gray: np.ndarray) -> np.ndarray:
    """Choose Otsu or adaptive threshold based on image std deviation."""
    std = float(np.std(gray))
    if std > 20.0:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
    return binary


def _morphology(binary: np.ndarray, ksize: int) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


def _blob_stats(binary: np.ndarray, params: dict) -> list[dict]:
    """
    Run connectedComponentsWithStats and return list of per-blob stat dicts
    that pass the area / circularity / aspect_ratio / solidity filters.
    """
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    area_min = params["area_min"]
    area_max = params["area_max"]
    circ_min = params["circularity_min"]
    ar_max = params["aspect_ratio_max"]
    sol_min = params["solidity_min"]

    blobs = []
    for i in range(1, n):  # skip background label 0
        area = float(stats[i, cv2.CC_STAT_AREA])
        if not (area_min <= area <= area_max):
            continue

        w = float(stats[i, cv2.CC_STAT_WIDTH])
        h = float(stats[i, cv2.CC_STAT_HEIGHT])
        ar = max(w, h) / max(min(w, h), 1.0)
        if ar > ar_max:
            continue

        # Circularity approximation from component mask
        mask = (labels == i).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = contours[0]
        perimeter = cv2.arcLength(contour, True)
        circularity = (4.0 * np.pi * area / (perimeter ** 2)) if perimeter > 0 else 0.0
        if circularity < circ_min:
            continue

        hull = cv2.convexHull(contour)
        hull_area = float(cv2.contourArea(hull))
        solidity = (area / hull_area) if hull_area > 0 else 0.0
        if solidity < sol_min:
            continue

        blobs.append({
            "label": i,
            "area": area,
            "cx": float(centroids[i][0]),
            "cy": float(centroids[i][1]),
            "circularity": circularity,
            "aspect_ratio": ar,
            "solidity": solidity,
            "x": int(stats[i, cv2.CC_STAT_LEFT]),
            "y": int(stats[i, cv2.CC_STAT_TOP]),
            "w": int(w),
            "h": int(h),
        })
    return blobs


def _process_image(image: np.ndarray, roi: Optional[ROIConfig], preset: dict) -> list[dict]:
    """Full preprocessing + blob detection pipeline for a single image."""
    cropped = _crop_roi(image, roi)
    gray = _to_gray(cropped)
    blurred = cv2.GaussianBlur(gray, (preset["blur_ksize"], preset["blur_ksize"]), 0)
    binary = _binarize(blurred)
    morphed = _morphology(binary, preset["morph_kernel"])
    return _blob_stats(morphed, preset)


def _compute_ok_pass_rate(
    ok_images: list[np.ndarray],
    roi: Optional[ROIConfig],
    preset: dict,
    expected_count_range: tuple[int, int],
) -> float:
    """Fraction of OK images where blob count falls in expected_count_range."""
    if not ok_images:
        return 0.0
    lo, hi = expected_count_range
    passed = sum(
        1 for img in ok_images
        if lo <= len(_process_image(img, roi, preset)) <= hi
    )
    return passed / len(ok_images)


def _compute_ng_detect_rate(
    ng_images: list[np.ndarray],
    roi: Optional[ROIConfig],
    preset: dict,
    expected_count_range: tuple[int, int],
) -> float:
    """Fraction of NG images where blob count falls OUTSIDE expected_count_range."""
    if not ng_images:
        return 0.0
    lo, hi = expected_count_range
    detected = sum(
        1 for img in ng_images
        if not (lo <= len(_process_image(img, roi, preset)) <= hi)
    )
    return detected / len(ng_images)


def _estimate_expected_range(
    ok_images: list[np.ndarray],
    roi: Optional[ROIConfig],
    preset: dict,
) -> tuple[int, int]:
    """
    Estimate the expected blob count range from OK images.
    Returns (floor, ceil) of ±1 around the median count.
    """
    counts = [len(_process_image(img, roi, preset)) for img in ok_images]
    if not counts:
        return (0, 0)
    median = sorted(counts)[len(counts) // 2]
    return (max(0, median - 1), median + 1)


def _draw_overlay(
    image: np.ndarray,
    blobs: list[dict],
    candidate_id: str,
) -> Optional[str]:
    """
    Draw blob bounding boxes and centroids on image, save PNG, return path.
    Returns None on any failure.
    """
    try:
        _OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
        overlay = image.copy()
        if overlay.ndim == 2:
            overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)
        for b in blobs:
            x, y, w, h = b["x"], b["y"], b["w"], b["h"]
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(overlay, (int(b["cx"]), int(b["cy"])), 4, (0, 0, 255), -1)
        out_path = _OVERLAY_DIR / f"{candidate_id}.png"
        cv2.imwrite(str(out_path), overlay)
        return str(out_path)
    except Exception as exc:
        logger.warning("Overlay generation failed for %s: %s", candidate_id, exc)
        return None


def _build_design_doc(
    preset: dict,
    expected_range: tuple[int, int],
    ok_blob_counts: list[int],
    ok_pass_rate: float,
    ng_detect_rate: float,
) -> dict:
    label = preset["label"]
    median_count = sorted(ok_blob_counts)[len(ok_blob_counts) // 2] if ok_blob_counts else 0
    return {
        "layout": {
            "description": f"Blob inspection — {label} threshold preset",
            "expected_blob_count_range": list(expected_range),
            "area_range_px2": [preset["area_min"], preset["area_max"]],
            "filter_chain": [
                f"GaussianBlur(ksize={preset['blur_ksize']})",
                "Threshold (Otsu if std>20 else AdaptiveGaussian)",
                f"MorphOpen+Close(kernel={preset['morph_kernel']})",
                "connectedComponentsWithStats",
                "area / circularity / aspect_ratio / solidity filter",
            ],
        },
        "parameters": {
            "area_min": preset["area_min"],
            "area_max": preset["area_max"],
            "circularity_min": preset["circularity_min"],
            "aspect_ratio_max": preset["aspect_ratio_max"],
            "solidity_min": preset["solidity_min"],
            "blur_ksize": preset["blur_ksize"],
            "morph_kernel": preset["morph_kernel"],
        },
        "result_calculation": {
            "method": "blob_count_range_check",
            "pass_condition": (
                f"blob_count in [{expected_range[0]}, {expected_range[1]}]"
            ),
            "score_formula": "score = ok_pass_rate * 0.5 + ng_detect_rate * 0.5",
            "ok_pass_rate": round(ok_pass_rate, 4),
            "ng_detect_rate": round(ng_detect_rate, 4),
        },
        "rationale": {
            "preset_label": label,
            "median_ok_blob_count": median_count,
            "selection_basis": (
                f"Preset '{label}': area [{preset['area_min']}, {preset['area_max']}], "
                f"circularity>={preset['circularity_min']:.2f}, "
                f"aspect_ratio<={preset['aspect_ratio_max']:.1f}, "
                f"solidity>={preset['solidity_min']:.2f}. "
                f"OK pass rate {ok_pass_rate:.1%}, NG detect rate {ng_detect_rate:.1%}."
            ),
        },
    }


# ─── Main engine ──────────────────────────────────────────────────────────────

class BlobInspectionEngine:
    """
    Blob-detection-based inspection engine.

    Generates three InspectionCandidate objects (strict / moderate / loose)
    from OK and NG image sets, ranks them by score, and attaches:
    - 4-section design document
    - Keyence / Cognex / Halcon / MIL library mapping
    - Overlay image (drawn on first OK image)

    CPU-only — no GPU, no deep learning.
    """

    def get_strategy_name(self) -> str:
        return "Blob Detection"

    def run(
        self,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        roi: Optional[ROIConfig] = None,
        purpose: Optional[InspectionPurpose] = None,
    ) -> list[InspectionCandidate]:
        """
        Generate and evaluate blob inspection candidates.

        Args:
            ok_images: List of OK (pass) reference images. Must be non-empty.
            ng_images: List of NG (fail) images. May be empty.
            roi: Optional ROI crop applied before processing.
            purpose: Optional inspection purpose metadata (informational only).

        Returns:
            List of InspectionCandidate sorted by score descending.

        Raises:
            InputValidationError: If ok_images is empty.
        """
        if not ok_images:
            raise InputValidationError("At least one OK image is required")

        candidates: list[InspectionCandidate] = []

        for preset in _PRESETS:
            candidate_id = f"blob_{preset['id_suffix']}"
            try:
                candidate = self._build_candidate(
                    candidate_id=candidate_id,
                    preset=preset,
                    ok_images=ok_images,
                    ng_images=ng_images,
                    roi=roi,
                )
                candidates.append(candidate)
                logger.info(
                    "Candidate %s: ok_pass=%.3f ng_detect=%.3f score=%.3f",
                    candidate_id,
                    candidate.ok_pass_rate,
                    candidate.ng_detect_rate,
                    candidate.score,
                )
            except Exception as exc:
                logger.error("Candidate %s failed: %s — skipping", candidate_id, exc)
                continue

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_candidate(
        self,
        candidate_id: str,
        preset: dict,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        roi: Optional[ROIConfig],
    ) -> InspectionCandidate:
        expected_range = _estimate_expected_range(ok_images, roi, preset)

        ok_pass_rate = _compute_ok_pass_rate(ok_images, roi, preset, expected_range)
        ng_detect_rate = _compute_ng_detect_rate(ng_images, roi, preset, expected_range)

        score = ok_pass_rate * 0.5 + ng_detect_rate * 0.5

        ok_blob_counts = [len(_process_image(img, roi, preset)) for img in ok_images]

        design_doc = _build_design_doc(
            preset=preset,
            expected_range=expected_range,
            ok_blob_counts=ok_blob_counts,
            ok_pass_rate=ok_pass_rate,
            ng_detect_rate=ng_detect_rate,
        )

        params = {
            "area_min": preset["area_min"],
            "area_max": preset["area_max"],
            "circularity_min": preset["circularity_min"],
            "aspect_ratio_max": preset["aspect_ratio_max"],
            "solidity_min": preset["solidity_min"],
            "blur_ksize": preset["blur_ksize"],
            "morph_kernel": preset["morph_kernel"],
        }

        library_mapping = _build_library_mapping(params)

        # Overlay on first OK image
        first_ok_blobs = _process_image(ok_images[0], roi, preset)
        first_ok_cropped = _crop_roi(ok_images[0], roi)
        overlay_path = _draw_overlay(first_ok_cropped, first_ok_blobs, candidate_id)

        rationale = (
            f"Preset '{preset['label']}' selected: "
            f"area [{preset['area_min']}, {preset['area_max']}] px², "
            f"circularity>={preset['circularity_min']:.2f}, "
            f"solidity>={preset['solidity_min']:.2f}. "
            f"Score={score:.3f} (OK pass={ok_pass_rate:.1%}, NG detect={ng_detect_rate:.1%})."
        )

        return InspectionCandidate(
            candidate_id=candidate_id,
            method="blob",
            params=params,
            design_doc=design_doc,
            library_mapping=library_mapping,
            ok_pass_rate=ok_pass_rate,
            ng_detect_rate=ng_detect_rate,
            score=score,
            rationale=rationale,
            overlay_image_path=overlay_path,
        )
