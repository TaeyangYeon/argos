"""
Pattern-based Inspection Engine (Argos Step 37).

Detects defects by comparing a test image against an OK reference image
via absolute difference (absdiff), thresholding, and morphological cleanup.
Three candidates with varying sensitivity are generated and evaluated against
OK/NG image sets.

CPU-only — NumPy and OpenCV only. No scikit-image, no torch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from core.models import InspectionResult, ROIConfig

logger = logging.getLogger("argos.inspection.pattern")

# Default pass threshold: defect area ratio (%) above which a test image is NG
PASS_SCORE = 5.0


# ─── Candidate descriptor ─────────────────────────────────────────────────────

@dataclass
class PatternInspectionCandidate:
    """Parameter preset for one pattern (difference-based) inspection candidate."""

    threshold: int
    min_area: int
    blur_kernel: int
    morph_kernel_size: int
    candidate_id: str
    design_doc: dict = field(default_factory=dict)
    library_mapping: dict = field(default_factory=dict)


# ─── Engine ───────────────────────────────────────────────────────────────────

class PatternInspectionEngine:
    """
    Difference-based (pattern subtraction) inspection engine.

    Compares a test image against the first OK reference image using absolute
    difference, thresholding, and morphological cleanup to isolate defect regions.
    Generates three ranked PatternInspectionCandidate objects with 4-section
    design documents and library-mapping tables.

    Three preset sensitivity levels:
      - strict    (threshold=30, min_area=50) — minimises false positives
      - balanced  (threshold=20, min_area=30) — balanced detection
      - sensitive (threshold=10, min_area=10) — maximises NG recall

    CPU-only — NumPy and OpenCV only.
    """

    PASS_SCORE: float = PASS_SCORE

    def get_strategy_name(self) -> str:
        """Return the human-readable strategy name."""
        return "PatternInspection"

    # ── Public interface ──────────────────────────────────────────────────────

    def generate_candidates(
        self,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        roi: Optional[ROIConfig] = None,
    ) -> list[PatternInspectionCandidate]:
        """
        Generate three inspection candidates with varying sensitivity.

        Candidate 1 (strict):    threshold=30, min_area=50 — low FP focus
        Candidate 2 (balanced):  threshold=20, min_area=30 — balanced
        Candidate 3 (sensitive): threshold=10, min_area=10 — high NG recall

        Args:
            ok_images: List of OK reference images (used for API consistency).
            ng_images: List of NG images (used for API consistency).
            roi:       Optional ROI crop (used for API consistency).

        Returns:
            List of three PatternInspectionCandidate objects.
        """
        presets = [
            {
                "id": "pattern_strict",
                "threshold": 30,
                "min_area": 50,
                "blur_kernel": 5,
                "morph_kernel_size": 3,
            },
            {
                "id": "pattern_balanced",
                "threshold": 20,
                "min_area": 30,
                "blur_kernel": 5,
                "morph_kernel_size": 3,
            },
            {
                "id": "pattern_sensitive",
                "threshold": 10,
                "min_area": 10,
                "blur_kernel": 3,
                "morph_kernel_size": 3,
            },
        ]

        candidates: list[PatternInspectionCandidate] = []
        for p in presets:
            c = PatternInspectionCandidate(
                threshold=p["threshold"],
                min_area=p["min_area"],
                blur_kernel=p["blur_kernel"],
                morph_kernel_size=p["morph_kernel_size"],
                candidate_id=p["id"],
            )
            c.design_doc = self._build_design_doc(c)
            c.library_mapping = self._build_library_mapping()
            candidates.append(c)

        return candidates

    def run(
        self,
        candidate: PatternInspectionCandidate,
        ok_images: list[np.ndarray],
        ng_images: list[np.ndarray],
        roi: Optional[ROIConfig] = None,
    ) -> InspectionResult:
        """
        Evaluate a candidate against OK and NG image sets.

        Uses ok_images[0] as the reference for difference computation.
        OK images should score below PASS_SCORE (no false positives).
        NG images should score at or above PASS_SCORE (defect detected).

        Args:
            candidate:  The PatternInspectionCandidate to evaluate.
            ok_images:  Non-empty list of OK (pass) reference images.
            ng_images:  Non-empty list of NG (fail) images.
            roi:        Optional ROI crop.

        Returns:
            InspectionResult with overlay_image highlighting defects on
            the first NG image.

        Raises:
            ValueError: If ok_images or ng_images is empty.
        """
        if not ok_images:
            raise ValueError("At least one OK image is required")
        if not ng_images:
            raise ValueError("At least one NG image is required")

        reference_gray = self._to_gray(ok_images[0])
        threshold = candidate.threshold
        min_area = candidate.min_area

        # Evaluate OK images — should all score below PASS_SCORE
        ok_scores = [
            self._compute_diff_score(
                reference_gray, self._to_gray(img), threshold, min_area, roi
            )
            for img in ok_images
        ]
        ok_passed = sum(1 for s in ok_scores if s < self.PASS_SCORE)
        ok_pass_rate = ok_passed / len(ok_images)

        # Evaluate NG images — should all score >= PASS_SCORE
        ng_scores = [
            self._compute_diff_score(
                reference_gray, self._to_gray(img), threshold, min_area, roi
            )
            for img in ng_images
        ]
        ng_detected = sum(1 for s in ng_scores if s >= self.PASS_SCORE)
        ng_detection_rate = ng_detected / len(ng_images)

        separation_score = (ok_pass_rate + ng_detection_rate) / 2.0
        is_ok = ok_pass_rate >= 0.8 and ng_detection_rate >= 0.8

        # Build overlay on first NG image
        overlay = self._build_overlay(
            reference_gray,
            self._to_gray(ng_images[0]),
            threshold,
            min_area,
            roi,
            ng_images[0],
        )

        logger.info(
            "Candidate %s: ok_pass=%.3f ng_detect=%.3f score=%.3f",
            candidate.candidate_id,
            ok_pass_rate,
            ng_detection_rate,
            separation_score,
        )

        return InspectionResult(
            success=True,
            strategy_name=self.get_strategy_name(),
            score=separation_score,
            is_ok=is_ok,
            overlay_image=overlay,
            best_candidate=candidate,
        )

    # ── Core scoring ──────────────────────────────────────────────────────────

    def _compute_diff_score(
        self,
        reference_gray: np.ndarray,
        test_gray: np.ndarray,
        threshold: int,
        min_area: int,
        roi: Optional[ROIConfig] = None,
    ) -> float:
        """
        Compute the defect area ratio between reference and test images.

        Pipeline:
          1. Crop both images to ROI (if provided)
          2. GaussianBlur both images to reduce noise
          3. Compute absolute difference (absdiff)
          4. Threshold the difference image
          5. Morphological opening to remove noise blobs
          6. Find contours and sum area of blobs >= min_area
          7. Return defect_area / roi_area * 100

        Args:
            reference_gray: Reference (OK) grayscale image.
            test_gray:      Test image to compare against reference.
            threshold:      Pixel difference threshold for binarisation.
            min_area:       Minimum contour area (px²) to count as defect.
            roi:            Optional ROI crop (applied in original-image coords).

        Returns:
            Defect area ratio as a percentage in [0.0, 100.0].
        """
        # Crop to ROI
        if roi is not None:
            ref = reference_gray[roi.y: roi.y + roi.height, roi.x: roi.x + roi.width]
            tst = test_gray[roi.y: roi.y + roi.height, roi.x: roi.x + roi.width]
        else:
            ref = reference_gray
            tst = test_gray

        roi_area = float(ref.shape[0] * ref.shape[1])
        if roi_area == 0:
            return 0.0

        # Blur to suppress high-frequency noise
        blur_k = 5
        ref_blur = cv2.GaussianBlur(ref, (blur_k, blur_k), 0)
        tst_blur = cv2.GaussianBlur(tst, (blur_k, blur_k), 0)

        # Absolute difference
        diff = cv2.absdiff(ref_blur, tst_blur)

        # Threshold — pixels with diff > threshold become 255
        _, binary = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

        # Morphological opening — removes small isolated noise blobs
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Sum area of qualifying contours
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        defect_area = sum(
            cv2.contourArea(c) for c in contours if cv2.contourArea(c) >= min_area
        )

        return defect_area / roi_area * 100.0

    # ── Overlay ───────────────────────────────────────────────────────────────

    def _build_overlay(
        self,
        reference_gray: np.ndarray,
        test_gray: np.ndarray,
        threshold: int,
        min_area: int,
        roi: Optional[ROIConfig],
        original_test: np.ndarray,
    ) -> np.ndarray:
        """
        Build a BGR overlay image with defect regions highlighted in red.

        Defect contours detected from the diff mask are drawn filled in red
        (0, 0, 255) on a copy of the original test image.

        Args:
            reference_gray: Reference grayscale image.
            test_gray:      Test grayscale image.
            threshold:      Difference threshold.
            min_area:       Minimum defect contour area (px²).
            roi:            Optional ROI (coords in original image space).
            original_test:  Original test image (BGR or grayscale) for base overlay.

        Returns:
            BGR uint8 ndarray with defect regions highlighted.
        """
        # Start from colour copy of original test
        if original_test.ndim == 2:
            overlay = cv2.cvtColor(original_test, cv2.COLOR_GRAY2BGR)
        else:
            overlay = original_test.copy()

        # Compute diff within ROI
        if roi is not None:
            ref = reference_gray[roi.y: roi.y + roi.height, roi.x: roi.x + roi.width]
            tst = test_gray[roi.y: roi.y + roi.height, roi.x: roi.x + roi.width]
        else:
            ref = reference_gray
            tst = test_gray

        blur_k = 5
        ref_blur = cv2.GaussianBlur(ref, (blur_k, blur_k), 0)
        tst_blur = cv2.GaussianBlur(tst, (blur_k, blur_k), 0)
        diff = cv2.absdiff(ref_blur, tst_blur)
        _, binary = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        valid = [c for c in contours if cv2.contourArea(c) >= min_area]

        if roi is not None:
            # Offset contours back to original image coordinates
            offset = np.array([[[roi.x, roi.y]]])
            valid = [c + offset for c in valid]

        cv2.drawContours(overlay, valid, -1, (0, 0, 255), -1)
        return overlay

    # ── Design doc ────────────────────────────────────────────────────────────

    def _build_design_doc(self, candidate: PatternInspectionCandidate) -> dict:
        """
        Build the mandatory 4-section design document for one candidate.

        Sections (Korean keys match project convention):
          배치구조    — inspection type, reference source, comparison method
          개별파라미터 — threshold, min_area, blur_kernel, morph_kernel_size, condition
          결과계산    — defect_area / roi_area * 100 → pass/fail threshold
          선택근거    — image contrast, noise level, defect shape complexity

        Args:
            candidate: The PatternInspectionCandidate to document.

        Returns:
            JSON-serialisable dict with the four required keys.
        """
        _label_map: dict[str, tuple[str, str]] = {
            "pattern_strict": (
                "strict",
                "고 정밀 모드 — 임계값 높게 설정, 노이즈·저대비 차이 무시. FP 최소화 목적",
            ),
            "pattern_balanced": (
                "balanced",
                "균형 모드 — OK 통과율과 NG 검출률 균형. 일반적 검사 환경에 적합",
            ),
            "pattern_sensitive": (
                "sensitive",
                "고 민감도 모드 — 임계값 낮게 설정, 미세 결함까지 검출. NG 재현율 최대화",
            ),
        }
        label, rationale_text = _label_map.get(
            candidate.candidate_id, ("custom", "사용자 정의 파라미터")
        )

        return {
            "배치구조": {
                "검사_유형": "차분 기반 결함 검사 (Difference-based Defect Detection)",
                "기준_이미지_출처": "OK 이미지 집합의 첫 번째 이미지 (ok_images[0])",
                "비교_방법": (
                    "GaussianBlur → cv2.absdiff → 임계값 이진화 "
                    "→ MorphOpen → 윤곽 면적 합산"
                ),
                "오버레이_방식": "첫 번째 NG 이미지 위에 결함 영역을 빨간색(0,0,255)으로 채움",
            },
            "개별파라미터": {
                "threshold": candidate.threshold,
                "min_area_px2": candidate.min_area,
                "blur_kernel": candidate.blur_kernel,
                "morph_kernel_size": candidate.morph_kernel_size,
                "condition": label,
                "pass_score_pct": self.PASS_SCORE,
            },
            "결과계산": {
                "방법": "defect_area / roi_area × 100 (%) 계산",
                "ok_판정_조건": f"diff_score < {self.PASS_SCORE} → OK (FP 없음)",
                "ng_판정_조건": f"diff_score ≥ {self.PASS_SCORE} → NG (결함 검출)",
                "점수_공식": (
                    "separation_score = (ok_pass_rate + ng_detection_rate) / 2"
                ),
                "ok_pass_rate_정의": "OK 이미지 중 diff_score < pass_score 비율",
                "ng_detection_rate_정의": "NG 이미지 중 diff_score ≥ pass_score 비율",
            },
            "선택근거": {
                "candidate_label": label,
                "선택_이유": rationale_text,
                "이미지_대비": (
                    "절대 차분값 기반 → 이미지 대비가 높을수록 결함 검출 정밀도 향상"
                ),
                "노이즈_수준": (
                    f"GaussianBlur(kernel={candidate.blur_kernel}) + "
                    f"MorphOpen(kernel={candidate.morph_kernel_size})으로 노이즈 억제"
                ),
                "결함_형상_복잡도": (
                    f"최소 {candidate.min_area}px² 이상 윤곽만 결함으로 인정 "
                    "→ 형상 복잡도 무관, 면적 기반 필터"
                ),
            },
        }

    # ── Library mapping ───────────────────────────────────────────────────────

    def _build_library_mapping(self) -> dict:
        """
        Return a Keyence / Cognex / Halcon / MIL parameter-name translation
        table for difference-based inspection concepts.

        Returns:
            Nested dict keyed by concept name, then by vendor.
        """
        return {
            "Difference Map": {
                "Keyence": "차분 검사",
                "Cognex":  "Difference Image",
                "Halcon":  "DiffImage",
                "MIL":     "MimArith",
            },
            "Threshold": {
                "Keyence": "2진화 임계값",
                "Cognex":  "Threshold",
                "Halcon":  "Threshold",
                "MIL":     "M_THRESHOLD",
            },
            "Min Area": {
                "Keyence": "최소 면적 필터",
                "Cognex":  "Minimum Blob Area",
                "Halcon":  "connection/select_shape",
                "MIL":     "M_AREA",
            },
            "Morphological": {
                "Keyence": "팽창/침식",
                "Cognex":  "Morphology",
                "Halcon":  "erosion/dilation",
                "MIL":     "MimMorphic",
            },
        }

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        """Convert BGR or grayscale image to single-channel uint8."""
        if image.ndim == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image.copy()
