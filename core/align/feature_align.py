"""
Feature-based Align Engine — Stage 3 Fallback (Argos Align Fallback Chain).

Uses ORB as the primary descriptor. Falls back to SIFT when ORB produces fewer
than *min_matches* good matches and SIFT is available in the installed OpenCV
build (cv2.SIFT_create).  All processing is CPU-only.

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

# ─── Library-name mapping (Keyence / Cognex / Halcon / MIL) ─────────────────

_LIBRARY_MAPPING: dict[str, str] = {
    "Keyence": "Feature Matching (AutoML search tool / pattern tool)",
    "Cognex": "PatMax Patterns — feature-based alignment",
    "Halcon": "find_scaled_shape_model / find_aniso_shape_model",
    "MIL": "MpatSearchContext (M_GEOMETRIC / M_EDGE_BASED)",
}


# ─── Extended result ──────────────────────────────────────────────────────────

@dataclass
class FeatureAlignResult(AlignResult):
    """AlignResult extended with feature-matching-specific output fields."""

    design_doc: dict = field(default_factory=dict)
    overlay_image: Optional[np.ndarray] = field(default=None)
    good_match_count: int = 0
    total_keypoint_count: int = 0
    descriptor_type: str = "ORB"

    @property
    def match_score(self) -> float:
        """Alias for score (good_matches / total_keypoints)."""
        return self.score


# ─── Engine ───────────────────────────────────────────────────────────────────

class FeatureAlignEngine(IAlignEngine):
    """
    ORB-based (optional SIFT fallback) feature alignment engine.

    Implements :class:`IAlignEngine` as Stage 3A of the Argos Align Fallback
    Chain.  Reference keypoints are computed lazily from the *reference* image
    on the first :meth:`run` call and cached for all subsequent calls.

    Args:
        min_matches: Minimum good-match count required for success.  Default 8.
        ratio: Lowe's ratio-test threshold.  Default 0.75.
        roi: Optional ROI; image and reference are cropped before processing.
    """

    def __init__(
        self,
        min_matches: int = 8,
        ratio: float = 0.75,
        roi: Optional[ROIConfig] = None,
    ) -> None:
        self._min_matches = min_matches
        self._ratio = ratio
        self._roi = roi

        # Lazy-initialised reference state
        self._ref_initialized: bool = False
        self._ref_kp_orb: list = []
        self._ref_des_orb: Optional[np.ndarray] = None
        self._ref_kp_sift: list = []
        self._ref_des_sift: Optional[np.ndarray] = None

        # Last overlay image (used by save_overlay_image)
        self._last_overlay: Optional[np.ndarray] = None

    # ── IAlignEngine interface ────────────────────────────────────────────────

    def run(self, image: np.ndarray, reference: np.ndarray) -> FeatureAlignResult:
        """
        Align *image* to *reference* using ORB (fallback SIFT) feature matching.

        Args:
            image: Input image to align (BGR or grayscale).
            reference: Reference image used to compute (and cache) keypoints.

        Returns:
            :class:`FeatureAlignResult` with success flag, score, transform, and
            four-section design document.
        """
        gray_img = self._to_gray(self._crop_roi(image))
        gray_ref = self._to_gray(self._crop_roi(reference))

        # Lazy initialisation from first reference image
        if not self._ref_initialized:
            self._init_reference(gray_ref)

        # ── Detect ORB keypoints on the current image ─────────────────────
        orb = cv2.ORB_create()
        img_kp_orb, img_des_orb = orb.detectAndCompute(gray_img, None)
        img_kp_orb = img_kp_orb or []

        good_orb = self._match(
            self._ref_des_orb, img_des_orb,
            self._ref_kp_orb, img_kp_orb,
            cv2.NORM_HAMMING,
        )

        if len(good_orb) >= self._min_matches:
            good = good_orb
            ref_kp = self._ref_kp_orb
            img_kp = img_kp_orb
            descriptor_type = "ORB"
        else:
            # ── SIFT fallback ────────────────────────────────────────────
            good_sift: list = []
            img_kp_sift: list = []
            if self._ref_des_sift is not None:
                try:
                    sift = cv2.SIFT_create()
                    img_kp_sift, img_des_sift = sift.detectAndCompute(gray_img, None)
                    img_kp_sift = img_kp_sift or []
                    good_sift = self._match(
                        self._ref_des_sift, img_des_sift,
                        self._ref_kp_sift, img_kp_sift,
                        cv2.NORM_L2,
                    )
                except AttributeError:
                    pass

            if len(good_sift) >= self._min_matches:
                good = good_sift
                ref_kp = self._ref_kp_sift
                img_kp = img_kp_sift
                descriptor_type = "SIFT"
            else:
                # Both ORB and SIFT insufficient — report failure
                total_kp = max(len(self._ref_kp_orb), len(img_kp_orb), 1)
                score = len(good_orb) / total_kp
                return self._failure(
                    f"Insufficient matches: {len(good_orb)} < {self._min_matches}",
                    good_count=len(good_orb),
                    total_kp=total_kp,
                    score=score,
                    descriptor_type="ORB",
                )

        # ── Compute homography ────────────────────────────────────────────
        total_kp = max(len(ref_kp), len(img_kp), 1)
        score = len(good) / total_kp

        src_pts = np.float32([ref_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([img_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M: Optional[np.ndarray] = None
        if len(good) >= 4:
            M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        # ── Build overlay ─────────────────────────────────────────────────
        gray_ref_bgr = cv2.cvtColor(gray_ref, cv2.COLOR_GRAY2BGR)
        gray_img_bgr = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
        overlay = cv2.drawMatches(
            gray_ref_bgr, ref_kp,
            gray_img_bgr, img_kp,
            good, None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
        )
        self._last_overlay = overlay

        design_doc = self._build_design_doc(len(good), total_kp, score, descriptor_type)

        return FeatureAlignResult(
            success=True,
            strategy_name=self.get_strategy_name(),
            score=score,
            transform_matrix=M,
            design_doc=design_doc,
            overlay_image=overlay,
            good_match_count=len(good),
            total_keypoint_count=total_kp,
            descriptor_type=descriptor_type,
        )

    def get_strategy_name(self) -> str:
        return "Feature Matching"

    def align(
        self,
        image: np.ndarray,
        reference: np.ndarray,
        roi: Optional[ROIConfig] = None,
    ) -> FeatureAlignResult:
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
        """Compute and cache ORB (and optionally SIFT) reference descriptors."""
        orb = cv2.ORB_create()
        kp, des = orb.detectAndCompute(gray_ref, None)
        self._ref_kp_orb = kp or []
        self._ref_des_orb = des

        # SIFT (optional — fails silently if not available)
        try:
            sift = cv2.SIFT_create()
            kp_s, des_s = sift.detectAndCompute(gray_ref, None)
            self._ref_kp_sift = kp_s or []
            self._ref_des_sift = des_s
        except AttributeError:
            self._ref_kp_sift = []
            self._ref_des_sift = None

        self._ref_initialized = True

    def _match(
        self,
        des1: Optional[np.ndarray],
        des2: Optional[np.ndarray],
        kp1: list,
        kp2: list,
        norm_type: int,
    ) -> list:
        """BFMatcher knnMatch + Lowe's ratio test."""
        if des1 is None or des2 is None:
            return []
        if len(kp1) < 2 or len(kp2) < 2:
            return []
        try:
            bf = cv2.BFMatcher(norm_type, crossCheck=False)
            raw = bf.knnMatch(des1, des2, k=2)
        except cv2.error:
            return []
        good = []
        for pair in raw:
            if len(pair) == 2:
                m, n = pair
                if m.distance < self._ratio * n.distance:
                    good.append(m)
        return good

    def _failure(
        self,
        reason: str,
        good_count: int = 0,
        total_kp: int = 0,
        score: float = 0.0,
        descriptor_type: str = "ORB",
    ) -> FeatureAlignResult:
        design_doc = self._build_design_doc(good_count, total_kp, score, descriptor_type)
        return FeatureAlignResult(
            success=False,
            strategy_name=self.get_strategy_name(),
            score=score,
            failure_reason=reason,
            design_doc=design_doc,
            good_match_count=good_count,
            total_keypoint_count=total_kp,
            descriptor_type=descriptor_type,
        )

    def _build_design_doc(
        self,
        good_count: int,
        total_kp: int,
        score: float,
        descriptor_type: str,
    ) -> dict:
        return {
            "placement": {
                "algorithm": f"{descriptor_type} Feature Matching",
                "stage": "Stage 3A — Fallback after Pattern + Caliper failure",
                "roi_applied": self._roi is not None,
                "library_mapping": _LIBRARY_MAPPING,
            },
            "parameters": {
                "descriptor": descriptor_type,
                "matcher": "BFMatcher (Hamming for ORB / L2 for SIFT)",
                "ratio_threshold": self._ratio,
                "min_matches": self._min_matches,
            },
            "result_calculation": {
                "good_matches": good_count,
                "total_keypoints": total_kp,
                "score": round(score, 4),
                "score_formula": "good_matches / total_keypoints",
            },
            "selection_rationale": {
                "reason": (
                    "ORB provides CPU-only, rotation-invariant feature detection "
                    "suitable for textured regions where template matching fails. "
                    "SIFT fallback improves recall on low-feature images."
                ),
                "failure_condition": f"good_matches < {self._min_matches}",
                "next_fallback": "ContourAlignEngine",
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
