"""
Feasibility Analyzer for Argos inspection results (Step 42).

Determines whether rule-based inspection is sufficient or whether
Edge Learning (EL) / Deep Learning (DL) is needed, based on the best
evaluation score, threshold, and optional AI analysis.

No image bytes are ever sent to the AI — the prompt is text-only.
"""

from __future__ import annotations

import re
from typing import Optional

from core.logger import get_logger
from core.models import EvaluationResult, FeasibilityResult, InspectionPurpose
from config.constants import (
    APPROACH_RULE_BASED,
    APPROACH_EDGE_LEARNING,
    APPROACH_DEEP_LEARNING,
)

logger = get_logger("evaluation.feasibility_analyzer")

# Model suggestion tables keyed by inspection_type
_EL_SUGGESTIONS: dict[str, str] = {
    "결함검출": "Anomaly detection (PatchCore)",
    "치수측정": "MobileNet-based classifier",
    "형상검사": "EfficientNet-Lite",
    "위치정렬": "MobileNet-based classifier",
    "기타": "MobileNet-based classifier",
}

_DL_SUGGESTIONS: dict[str, str] = {
    "결함검출": "Anomaly detection (PaDiM/PatchCore)",
    "치수측정": "ResNet/EfficientNet CNN classifier",
    "형상검사": "U-Net segmentation",
    "위치정렬": "YOLO object detection",
    "기타": "ResNet/EfficientNet CNN classifier",
}

_DL_SCORE_GAP = 30.0
_EL_SCORE_GAP = 15.0


class FeasibilityAnalyzer:
    """
    Analyses whether rule-based inspection is feasible or EL/DL is needed.

    Decision flow:
    1. If best_score >= threshold → RULE_BASED, feasible.
    2. If best_score < threshold → query AI for EL vs DL recommendation.
    3. On AI failure → local heuristic fallback based on score gap and features.
    """

    def __init__(self, ai_provider=None) -> None:
        """
        Initialise the analyser.

        Args:
            ai_provider: IAIProvider instance or None to skip AI analysis.
        """
        self._ai_provider = ai_provider

    def analyze(
        self,
        best_score: float,
        threshold: float,
        evaluation_result: EvaluationResult,
        inspection_purpose: InspectionPurpose,
        feature_summary: Optional[dict] = None,
    ) -> FeasibilityResult:
        """
        Determine feasibility of rule-based inspection.

        Args:
            best_score:         Best score achieved by the optimizer.
            threshold:          Minimum acceptable score.
            evaluation_result:  EvaluationResult from the best candidate.
            inspection_purpose: InspectionPurpose with inspection context.
            feature_summary:    Optional dict with keys like noise_level,
                                edge_strength, contrast, blob_count.

        Returns:
            FeasibilityResult with approach recommendation and reasoning.
        """
        if best_score >= threshold:
            return self._rule_based_result(best_score, threshold, evaluation_result)

        # Rule-based insufficient — determine EL vs DL
        return self._determine_advanced(
            best_score, threshold, evaluation_result, inspection_purpose, feature_summary
        )

    # ------------------------------------------------------------------ #
    #  Rule-based sufficient                                               #
    # ------------------------------------------------------------------ #

    def _rule_based_result(
        self,
        best_score: float,
        threshold: float,
        evaluation_result: EvaluationResult,
    ) -> FeasibilityResult:
        margin = best_score - threshold
        reasoning = (
            f"Rule-based 검사로 충분합니다. "
            f"최고 점수 {best_score:.1f}이(가) 임계값 {threshold:.1f}을(를) "
            f"{margin:.1f}점 초과했습니다. "
            f"OK 통과율: {evaluation_result.ok_pass_rate:.1%}, "
            f"NG 검출율: {evaluation_result.ng_detect_rate:.1%}."
        )
        return FeasibilityResult(
            rule_based_sufficient=True,
            recommended_approach=APPROACH_RULE_BASED,
            reasoning=reasoning,
            model_suggestion=None,
        )

    # ------------------------------------------------------------------ #
    #  Advanced (EL / DL) determination                                    #
    # ------------------------------------------------------------------ #

    def _determine_advanced(
        self,
        best_score: float,
        threshold: float,
        evaluation_result: EvaluationResult,
        inspection_purpose: InspectionPurpose,
        feature_summary: Optional[dict],
    ) -> FeasibilityResult:
        """Try AI first, fall back to heuristic on failure or no provider."""
        if self._ai_provider is not None:
            result = self._try_ai(
                best_score, threshold, evaluation_result, inspection_purpose, feature_summary
            )
            if result is not None:
                return result
            logger.warning("AI 분석 실패, 로컬 휴리스틱으로 대체합니다.")

        return self._heuristic_fallback(
            best_score, threshold, evaluation_result, inspection_purpose, feature_summary
        )

    # ------------------------------------------------------------------ #
    #  AI-based determination                                              #
    # ------------------------------------------------------------------ #

    def _try_ai(
        self,
        best_score: float,
        threshold: float,
        evaluation_result: EvaluationResult,
        inspection_purpose: InspectionPurpose,
        feature_summary: Optional[dict],
    ) -> Optional[FeasibilityResult]:
        prompt = self._build_prompt(
            best_score, threshold, evaluation_result, inspection_purpose, feature_summary
        )
        try:
            response: str = self._ai_provider.analyze_safe(prompt, fallback="")
            if not response.strip():
                return None
            return self._parse_ai_response(
                response, best_score, threshold, inspection_purpose
            )
        except Exception as exc:
            logger.warning("AI 호출 예외: %s", exc)
            return None

    def _build_prompt(
        self,
        best_score: float,
        threshold: float,
        evaluation_result: EvaluationResult,
        inspection_purpose: InspectionPurpose,
        feature_summary: Optional[dict],
    ) -> str:
        gap = threshold - best_score
        fp_count = len(evaluation_result.fp_images)
        fn_count = len(evaluation_result.fn_images)

        lines = [
            "Rule-based 검사가 임계값을 충족하지 못했습니다.",
            "아래 정보를 기반으로 Edge Learning 또는 Deep Learning 중 적합한 기술 수준을 판단하세요.",
            "",
            f"최고 점수: {best_score:.2f}",
            f"임계값: {threshold:.2f}",
            f"점수 갭: {gap:.2f}",
            f"분리 마진: {evaluation_result.margin:.1f}",
            f"FP(오탐) 수: {fp_count}",
            f"FN(미탐) 수: {fn_count}",
            "",
            f"검사 유형: {inspection_purpose.inspection_type}",
            f"검사 설명: {inspection_purpose.description}",
            f"OK/NG 기준: {inspection_purpose.ok_ng_criteria}",
            f"대상 특징: {inspection_purpose.target_feature}",
        ]

        if feature_summary:
            lines.append("")
            lines.append("이미지 특성:")
            for key in ("noise_level", "edge_strength", "contrast", "blob_count"):
                if key in feature_summary:
                    lines.append(f"  {key}: {feature_summary[key]}")

        lines.extend([
            "",
            "응답 형식:",
            "recommended_level: EDGE_LEARNING 또는 DEEP_LEARNING",
            "reasoning: 판단 근거를 한 문단으로 작성",
            "model_suggestions: 추천 모델을 쉼표로 구분하여 나열",
        ])
        return "\n".join(lines)

    def _parse_ai_response(
        self,
        response: str,
        best_score: float,
        threshold: float,
        inspection_purpose: InspectionPurpose,
    ) -> Optional[FeasibilityResult]:
        """Parse AI response to extract recommended level and reasoning."""
        text = response.strip()
        if not text:
            return None

        # Extract recommended_level
        level_match = re.search(
            r"recommended_level\s*:\s*(EDGE_LEARNING|DEEP_LEARNING)", text, re.IGNORECASE
        )
        if not level_match:
            # Try looser matching
            if "DEEP_LEARNING" in text.upper():
                level = "DEEP_LEARNING"
            elif "EDGE_LEARNING" in text.upper():
                level = "EDGE_LEARNING"
            else:
                return None
        else:
            level = level_match.group(1).upper()

        # Map to approach constant
        approach = APPROACH_DEEP_LEARNING if level == "DEEP_LEARNING" else APPROACH_EDGE_LEARNING

        # Extract reasoning
        reasoning_match = re.search(r"reasoning\s*:\s*(.+?)(?=model_suggestions|$)", text, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else text[:300]
        if not reasoning:
            reasoning = f"AI가 {approach}을(를) 권장합니다."

        # Extract model suggestions
        suggestions_match = re.search(r"model_suggestions\s*:\s*(.+)", text)
        if suggestions_match:
            model_suggestion = suggestions_match.group(1).strip()
        else:
            inspection_type = inspection_purpose.inspection_type
            table = _DL_SUGGESTIONS if level == "DEEP_LEARNING" else _EL_SUGGESTIONS
            model_suggestion = table.get(inspection_type, table.get("기타", ""))

        return FeasibilityResult(
            rule_based_sufficient=False,
            recommended_approach=approach,
            reasoning=reasoning,
            model_suggestion=model_suggestion,
        )

    # ------------------------------------------------------------------ #
    #  Local heuristic fallback                                            #
    # ------------------------------------------------------------------ #

    def _heuristic_fallback(
        self,
        best_score: float,
        threshold: float,
        evaluation_result: EvaluationResult,
        inspection_purpose: InspectionPurpose,
        feature_summary: Optional[dict],
    ) -> FeasibilityResult:
        gap = threshold - best_score
        noise_level = (feature_summary or {}).get("noise_level", "Low")

        # Determine level
        if gap > _DL_SCORE_GAP or noise_level == "High":
            approach = APPROACH_DEEP_LEARNING
            level_key = "DL"
        elif gap > _EL_SCORE_GAP or noise_level == "Medium":
            approach = APPROACH_EDGE_LEARNING
            level_key = "EL"
        else:
            approach = APPROACH_EDGE_LEARNING
            level_key = "EL"

        # Build reasoning
        fp_count = len(evaluation_result.fp_images)
        fn_count = len(evaluation_result.fn_images)
        parts = [
            f"Rule-based 최고 점수({best_score:.1f})가 임계값({threshold:.1f})에 미달합니다 (갭: {gap:.1f}).",
        ]
        if noise_level == "High":
            parts.append("이미지 노이즈가 높아 Deep Learning이 필요합니다.")
        elif noise_level == "Medium":
            parts.append("이미지 노이즈가 보통 수준으로 Edge Learning이 적합합니다.")
        if fp_count > 0 or fn_count > 0:
            parts.append(f"FP {fp_count}건, FN {fn_count}건이 발생했습니다.")
        parts.append(f"휴리스틱 분석 결과 {approach}을(를) 권장합니다.")
        reasoning = " ".join(parts)

        # Model suggestion
        inspection_type = inspection_purpose.inspection_type
        table = _DL_SUGGESTIONS if level_key == "DL" else _EL_SUGGESTIONS
        model_suggestion = table.get(inspection_type, table.get("기타", ""))

        return FeasibilityResult(
            rule_based_sufficient=False,
            recommended_approach=approach,
            reasoning=reasoning,
            model_suggestion=model_suggestion,
        )
