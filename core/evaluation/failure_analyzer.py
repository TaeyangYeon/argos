"""
Failure Analyzer for Argos inspection results (Step 41).

Accepts an OptimizationResult, generates OpenCV overlay images for every
false-positive and false-negative case, queries an optional AI provider for
root-cause analysis, and returns a FailureAnalysisResult.

No image bytes are ever sent to the AI — the prompt is text-only.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Optional

import cv2
import numpy as np

from core.interfaces import IFailureAnalyzer
from core.models import FailureAnalysisResult

logger = logging.getLogger("argos.evaluation.failure_analyzer")

# Overlay image dimensions for placeholder images
_OVERLAY_W = 320
_OVERLAY_H = 240

# BGR colour for failure indicators
_RED_BGR = (0, 0, 255)
_BORDER_THICKNESS = 6
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 1.0
_FONT_THICKNESS = 2

_AI_FALLBACK_SUMMARY = "AI 분석 불가"

# BGR colours for failure type borders
_FP_COLOR_BGR = (0, 0, 255)    # Red
_FN_COLOR_BGR = (0, 165, 255)  # Orange

_ID_RE = re.compile(r"^(ok|ng)_(\d+)$")


class FailureAnalyzer(IFailureAnalyzer):
    """
    Analyses failure cases from an OptimizationResult.

    For each false-positive (FP) and false-negative (FN) image identifier,
    an overlay image is created — using the original image as background
    when available, with a coloured border and failure-type label rendered
    via OpenCV.  An optional AI provider is queried for a text-only
    root-cause analysis.
    """

    def __init__(
        self,
        ai_provider=None,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        Initialise the analyser.

        Args:
            ai_provider: IAIProvider instance or None to skip AI analysis.
            output_dir:  Directory where overlay images are saved.
                         Defaults to a new temporary directory per analyser instance.
        """
        self._ai_provider = ai_provider
        self._output_dir: str = output_dir or tempfile.mkdtemp(prefix="argos_failure_")
        os.makedirs(self._output_dir, exist_ok=True)
        self._ok_images: Optional[list[np.ndarray]] = None
        self._ng_images: Optional[list[np.ndarray]] = None

    # ------------------------------------------------------------------ #
    #  IFailureAnalyzer public API                                         #
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        optimization_result: object,
        purpose: object = None,
        *,
        ok_images: Optional[list] = None,
        ng_images: Optional[list] = None,
    ) -> FailureAnalysisResult:
        """
        Run failure analysis on the best candidate from an OptimizationResult.

        Args:
            optimization_result: OptimizationResult from InspectionOptimizer.
            purpose:             Optional InspectionPurpose for AI context.
            ok_images:           Optional list of OK image arrays (np.ndarray).
                                 Used as overlay background for FP cases.
            ng_images:           Optional list of NG image arrays (np.ndarray).
                                 Used as overlay background for FN cases.

        Returns:
            FailureAnalysisResult with overlay paths, counts, and AI analysis.
        """
        self._ok_images = ok_images
        self._ng_images = ng_images

        best_candidate = getattr(optimization_result, "best_candidate", None)
        best_evaluation = getattr(optimization_result, "best_evaluation", None)

        fp_image_ids: list[str] = list(getattr(best_evaluation, "fp_images", []) or [])
        fn_image_ids: list[str] = list(getattr(best_evaluation, "fn_images", []) or [])

        fp_overlay_paths = self._generate_overlays(fp_image_ids, "FP")
        fn_overlay_paths = self._generate_overlays(fn_image_ids, "FN")

        cause_summary, improvement_directions = self._call_ai(
            best_candidate, best_evaluation, purpose, len(fp_image_ids), len(fn_image_ids)
        )

        return FailureAnalysisResult(
            fp_overlay_paths=fp_overlay_paths,
            fn_overlay_paths=fn_overlay_paths,
            cause_summary=cause_summary,
            improvement_directions=improvement_directions,
            fp_count=len(fp_image_ids),
            fn_count=len(fn_image_ids),
        )

    # ------------------------------------------------------------------ #
    #  Overlay generation                                                  #
    # ------------------------------------------------------------------ #

    def _generate_overlays(
        self,
        image_ids: list[str],
        label: str,
    ) -> list[str]:
        """
        Create one overlay PNG per image ID and return the saved paths.

        Failures are isolated — a single bad image ID never aborts the loop.
        """
        saved_paths: list[str] = []
        for image_id in image_ids:
            try:
                path = self._make_overlay(image_id, label)
                saved_paths.append(path)
            except Exception as exc:
                logger.warning("오버레이 생성 실패 (%s / %s): %s", label, image_id, exc)
        return saved_paths

    def _resolve_source_image(self, image_id: str) -> Optional[np.ndarray]:
        """Look up the original image array from the image_id (e.g. 'ok_0', 'ng_2')."""
        m = _ID_RE.match(image_id)
        if m is None:
            return None
        prefix, idx_str = m.group(1), int(m.group(2))
        if prefix == "ok" and self._ok_images and idx_str < len(self._ok_images):
            return self._ok_images[idx_str]
        if prefix == "ng" and self._ng_images and idx_str < len(self._ng_images):
            return self._ng_images[idx_str]
        return None

    def _make_overlay(self, image_id: str, label: str) -> str:
        """
        Create a single overlay image and save it to disk.

        Uses the original image as background when available; otherwise
        falls back to a gray placeholder canvas.

        Returns:
            Absolute path to the saved PNG file.
        """
        source = self._resolve_source_image(image_id)

        if source is not None and isinstance(source, np.ndarray) and source.size > 0:
            # Use the original image as background
            img = source.copy()
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            # Fallback: gray placeholder
            img = np.ones((_OVERLAY_H, _OVERLAY_W, 3), dtype=np.uint8) * 180

        h, w = img.shape[:2]
        border_color = _FP_COLOR_BGR if label == "FP" else _FN_COLOR_BGR

        # Coloured border
        cv2.rectangle(img, (0, 0), (w - 1, h - 1), border_color, _BORDER_THICKNESS)

        # Semi-transparent label background for readability
        label_text = f"{label}: {image_id}"
        (tw, th), baseline = cv2.getTextSize(label_text, _FONT, _FONT_SCALE, _FONT_THICKNESS)
        cv2.rectangle(img, (0, 0), (tw + 20, th + baseline + 20), border_color, cv2.FILLED)
        cv2.putText(img, label_text, (10, th + 10), _FONT, _FONT_SCALE, (255, 255, 255), _FONT_THICKNESS)

        safe_id = re.sub(r"[^\w\-]", "_", image_id)
        filename = f"{label}_{safe_id}.png"
        filepath = os.path.join(self._output_dir, filename)
        cv2.imwrite(filepath, img)
        return os.path.abspath(filepath)

    # ------------------------------------------------------------------ #
    #  AI analysis                                                         #
    # ------------------------------------------------------------------ #

    def _call_ai(
        self,
        best_candidate: object,
        best_evaluation: object,
        purpose: object,
        fp_count: int,
        fn_count: int,
    ) -> tuple[str, list[str]]:
        """
        Query the AI provider for failure root-cause analysis.

        Returns:
            (cause_summary, improvement_directions)
            Falls back to ("AI 분석 불가", []) if the provider is None or raises.
        """
        if self._ai_provider is None:
            return _AI_FALLBACK_SUMMARY, []

        prompt = self._build_prompt(best_candidate, best_evaluation, purpose, fp_count, fn_count)
        try:
            response: str = self._ai_provider.analyze_safe(prompt, fallback="")
            return _parse_ai_response(response)
        except Exception as exc:
            logger.warning("AI 분석 호출 실패: %s", exc)
            return _AI_FALLBACK_SUMMARY, []

    def _build_prompt(
        self,
        best_candidate: object,
        best_evaluation: object,
        purpose: object,
        fp_count: int,
        fn_count: int,
    ) -> str:
        """Build a text-only prompt for AI failure analysis."""
        engine_name: str = getattr(best_candidate, "engine_name", "Unknown")
        ok_pass_rate: float = float(getattr(best_evaluation, "ok_pass_rate", 0.0))
        ng_detect_rate: float = float(getattr(best_evaluation, "ng_detect_rate", 0.0))
        final_score: float = float(
            getattr(best_evaluation, "final_score", None)
            or getattr(best_evaluation, "score", 0.0)
            or 0.0
        )
        margin: float = float(getattr(best_evaluation, "margin", 0.0))
        is_warning: bool = bool(getattr(best_evaluation, "is_margin_warning", False))

        purpose_desc: str = getattr(purpose, "description", "") if purpose else ""
        inspection_type: str = getattr(purpose, "inspection_type", "") if purpose else ""
        ok_ng_criteria: str = getattr(purpose, "ok_ng_criteria", "") if purpose else ""

        return (
            "검사 실패 원인 분석을 요청합니다.\n\n"
            f"엔진: {engine_name}\n"
            f"최종 점수: {final_score:.2f}\n"
            f"OK 통과율: {ok_pass_rate:.2%}\n"
            f"NG 검출율: {ng_detect_rate:.2%}\n"
            f"분리 마진: {margin:.1f}\n"
            f"경계선 위험 구간: {'예' if is_warning else '아니오'}\n\n"
            f"FP(오탐) 수: {fp_count}\n"
            f"FN(미탐) 수: {fn_count}\n\n"
            f"검사 목적: {purpose_desc}\n"
            f"검사 유형: {inspection_type}\n"
            f"OK/NG 기준: {ok_ng_criteria}\n\n"
            "위 정보를 바탕으로:\n"
            "1. 실패 원인 요약(cause_summary)을 한 문단으로 작성하세요.\n"
            "2. 개선 방향(improvement_directions)을 '- ' 로 시작하는 항목으로 "
            "3~5개 작성하세요.\n"
        )


# ------------------------------------------------------------------ #
#  Module-level helpers                                                #
# ------------------------------------------------------------------ #

def _parse_ai_response(response: str) -> tuple[str, list[str]]:
    """
    Parse the AI provider's free-text response.

    Extracts:
    - cause_summary: first non-bullet paragraph (up to 500 chars)
    - improvement_directions: lines beginning with '- ', '* ', or digit + '.'
    """
    if not response or not response.strip():
        return _AI_FALLBACK_SUMMARY, []

    lines = response.strip().splitlines()
    summary_parts: list[str] = []
    directions: list[str] = []

    _bullet = re.compile(r"^[-*•]\s+(.+)")
    _numbered = re.compile(r"^\d+[.)]\s+(.+)")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = _bullet.match(stripped) or _numbered.match(stripped)
        if m:
            directions.append(m.group(1).strip())
        else:
            summary_parts.append(stripped)

    cause_summary = " ".join(summary_parts)[:500].strip() or _AI_FALLBACK_SUMMARY
    return cause_summary, directions
