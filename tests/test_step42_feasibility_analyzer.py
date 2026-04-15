"""
Tests for FeasibilityAnalyzer (Step 42).

Covers: rule-based sufficient, AI-based EL/DL determination,
AI failure fallback, heuristic logic, edge cases, and field validation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.evaluation.feasibility_analyzer import FeasibilityAnalyzer
from core.models import EvaluationResult, FeasibilityResult, InspectionPurpose
from config.constants import APPROACH_RULE_BASED, APPROACH_EDGE_LEARNING, APPROACH_DEEP_LEARNING


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

def _make_eval(
    ok_pass_rate: float = 0.9,
    ng_detect_rate: float = 0.8,
    final_score: float = 75.0,
    margin: float = 10.0,
    fp_images: list | None = None,
    fn_images: list | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        best_strategy="blob",
        ok_pass_rate=ok_pass_rate,
        ng_detect_rate=ng_detect_rate,
        final_score=final_score,
        margin=margin,
        is_margin_warning=margin < 15.0,
        fp_images=fp_images or [],
        fn_images=fn_images or [],
    )


def _make_purpose(inspection_type: str = "결함검출") -> InspectionPurpose:
    return InspectionPurpose(
        inspection_type=inspection_type,
        description="스크래치 검사",
        ok_ng_criteria="스크래치 없음",
        target_feature="표면 스크래치",
        measurement_unit="px",
        tolerance="±2px",
    )


def _ai_response_el() -> str:
    return (
        "recommended_level: EDGE_LEARNING\n"
        "reasoning: 점수 갭이 크지 않고 노이즈가 낮아 Edge Learning으로 충분합니다.\n"
        "model_suggestions: MobileNet-based classifier, EfficientNet-Lite"
    )


def _ai_response_dl() -> str:
    return (
        "recommended_level: DEEP_LEARNING\n"
        "reasoning: 높은 노이즈와 복잡한 결함 패턴으로 Deep Learning이 필요합니다.\n"
        "model_suggestions: ResNet/EfficientNet CNN classifier, YOLO object detection"
    )


# ------------------------------------------------------------------ #
#  1. Rule-based sufficient (score >= threshold)                       #
# ------------------------------------------------------------------ #

class TestRuleBasedSufficient:
    def test_score_above_threshold(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(80.0, 70.0, _make_eval(), _make_purpose())

        assert result.rule_based_sufficient is True
        assert result.recommended_approach == APPROACH_RULE_BASED
        assert result.model_suggestion is None
        assert result.reasoning

    def test_score_exactly_at_threshold(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(70.0, 70.0, _make_eval(), _make_purpose())

        assert result.rule_based_sufficient is True
        assert result.recommended_approach == APPROACH_RULE_BASED

    def test_perfect_score(self):
        analyzer = FeasibilityAnalyzer()
        ev = _make_eval(ok_pass_rate=1.0, ng_detect_rate=1.0, final_score=100.0)
        result = analyzer.analyze(100.0, 70.0, ev, _make_purpose())

        assert result.rule_based_sufficient is True
        assert "100.0" in result.reasoning

    def test_reasoning_includes_rates(self):
        analyzer = FeasibilityAnalyzer()
        ev = _make_eval(ok_pass_rate=0.95, ng_detect_rate=0.85)
        result = analyzer.analyze(85.0, 70.0, ev, _make_purpose())

        assert "95.0%" in result.reasoning
        assert "85.0%" in result.reasoning


# ------------------------------------------------------------------ #
#  2. AI determines EL                                                 #
# ------------------------------------------------------------------ #

class TestAIDeterminesEL:
    def test_ai_recommends_edge_learning(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = _ai_response_el()
        analyzer = FeasibilityAnalyzer(ai_provider=provider)

        result = analyzer.analyze(60.0, 70.0, _make_eval(final_score=60.0), _make_purpose())

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_EDGE_LEARNING
        assert result.reasoning
        assert result.model_suggestion
        provider.analyze_safe.assert_called_once()

    def test_ai_prompt_contains_purpose_fields(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = _ai_response_el()
        analyzer = FeasibilityAnalyzer(ai_provider=provider)
        purpose = _make_purpose("치수측정")

        analyzer.analyze(55.0, 70.0, _make_eval(final_score=55.0), purpose)

        prompt = provider.analyze_safe.call_args[0][0]
        assert "치수측정" in prompt
        assert "55.00" in prompt
        assert "70.00" in prompt


# ------------------------------------------------------------------ #
#  3. AI determines DL                                                 #
# ------------------------------------------------------------------ #

class TestAIDeterminesDL:
    def test_ai_recommends_deep_learning(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = _ai_response_dl()
        analyzer = FeasibilityAnalyzer(ai_provider=provider)

        result = analyzer.analyze(30.0, 70.0, _make_eval(final_score=30.0), _make_purpose())

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_DEEP_LEARNING
        assert "Deep Learning" in result.model_suggestion or "YOLO" in result.model_suggestion


# ------------------------------------------------------------------ #
#  4. AI failure → heuristic fallback to EL                            #
# ------------------------------------------------------------------ #

class TestAIFailureFallbackEL:
    def test_ai_returns_empty_falls_back_el(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = ""
        analyzer = FeasibilityAnalyzer(ai_provider=provider)

        # gap = 20, within 15~30 → EL
        result = analyzer.analyze(50.0, 70.0, _make_eval(final_score=50.0), _make_purpose())

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_EDGE_LEARNING
        assert "휴리스틱" in result.reasoning

    def test_ai_raises_exception_falls_back_el(self):
        provider = MagicMock()
        provider.analyze_safe.side_effect = Exception("network error")
        analyzer = FeasibilityAnalyzer(ai_provider=provider)

        result = analyzer.analyze(55.0, 70.0, _make_eval(final_score=55.0), _make_purpose())

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_EDGE_LEARNING


# ------------------------------------------------------------------ #
#  5. AI failure → heuristic fallback to DL                            #
# ------------------------------------------------------------------ #

class TestAIFailureFallbackDL:
    def test_ai_returns_empty_large_gap_falls_back_dl(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = ""
        analyzer = FeasibilityAnalyzer(ai_provider=provider)

        # gap = 40, > 30 → DL
        result = analyzer.analyze(30.0, 70.0, _make_eval(final_score=30.0), _make_purpose())

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_DEEP_LEARNING

    def test_no_provider_large_gap_dl(self):
        analyzer = FeasibilityAnalyzer(ai_provider=None)
        result = analyzer.analyze(35.0, 70.0, _make_eval(final_score=35.0), _make_purpose())

        assert result.recommended_approach == APPROACH_DEEP_LEARNING


# ------------------------------------------------------------------ #
#  6. Inspection type affects model suggestions                        #
# ------------------------------------------------------------------ #

class TestInspectionTypeModelSuggestions:
    def test_defect_detection_dl_suggestion(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(
            30.0, 70.0, _make_eval(final_score=30.0), _make_purpose("결함검출")
        )
        assert "PaDiM" in result.model_suggestion or "PatchCore" in result.model_suggestion

    def test_dimension_measurement_el_suggestion(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(
            55.0, 70.0, _make_eval(final_score=55.0), _make_purpose("치수측정")
        )
        assert "MobileNet" in result.model_suggestion

    def test_shape_inspection_dl_suggestion(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(
            30.0, 70.0, _make_eval(final_score=30.0), _make_purpose("형상검사")
        )
        assert "U-Net" in result.model_suggestion


# ------------------------------------------------------------------ #
#  7. Edge cases                                                       #
# ------------------------------------------------------------------ #

class TestEdgeCases:
    def test_zero_score(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(0.0, 70.0, _make_eval(final_score=0.0), _make_purpose())

        assert result.rule_based_sufficient is False
        assert result.recommended_approach == APPROACH_DEEP_LEARNING

    def test_score_just_below_threshold(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(69.9, 70.0, _make_eval(final_score=69.9), _make_purpose())

        assert result.rule_based_sufficient is False


# ------------------------------------------------------------------ #
#  8. FeasibilityResult field completeness                             #
# ------------------------------------------------------------------ #

class TestFieldCompleteness:
    def test_rule_based_result_all_fields(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(80.0, 70.0, _make_eval(), _make_purpose())

        assert isinstance(result, FeasibilityResult)
        assert isinstance(result.rule_based_sufficient, bool)
        assert isinstance(result.recommended_approach, str)
        assert isinstance(result.reasoning, str)
        # model_suggestion is None for rule-based
        assert result.model_suggestion is None

    def test_advanced_result_all_fields(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(50.0, 70.0, _make_eval(final_score=50.0), _make_purpose())

        assert isinstance(result, FeasibilityResult)
        assert isinstance(result.rule_based_sufficient, bool)
        assert isinstance(result.recommended_approach, str)
        assert isinstance(result.reasoning, str)
        assert isinstance(result.model_suggestion, str)
        assert len(result.model_suggestion) > 0


# ------------------------------------------------------------------ #
#  9. Reasoning always non-empty                                       #
# ------------------------------------------------------------------ #

class TestReasoningNonEmpty:
    def test_rule_based_reasoning(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(80.0, 70.0, _make_eval(), _make_purpose())
        assert len(result.reasoning) > 0

    def test_heuristic_reasoning(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(50.0, 70.0, _make_eval(final_score=50.0), _make_purpose())
        assert len(result.reasoning) > 0

    def test_ai_reasoning(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = _ai_response_el()
        analyzer = FeasibilityAnalyzer(ai_provider=provider)
        result = analyzer.analyze(60.0, 70.0, _make_eval(final_score=60.0), _make_purpose())
        assert len(result.reasoning) > 0


# ------------------------------------------------------------------ #
#  10. Separation margin influence                                     #
# ------------------------------------------------------------------ #

class TestSeparationMargin:
    def test_margin_included_in_ai_prompt(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = _ai_response_el()
        analyzer = FeasibilityAnalyzer(ai_provider=provider)
        ev = _make_eval(final_score=60.0, margin=5.2)

        analyzer.analyze(60.0, 70.0, ev, _make_purpose())

        prompt = provider.analyze_safe.call_args[0][0]
        assert "5.2" in prompt


# ------------------------------------------------------------------ #
#  11. Feature summary: high noise → DL bias                           #
# ------------------------------------------------------------------ #

class TestFeatureSummaryHighNoise:
    def test_high_noise_biases_to_dl(self):
        analyzer = FeasibilityAnalyzer()
        features = {"noise_level": "High", "edge_strength": 0.3, "contrast": 20, "blob_count": 5}
        # gap = 10 (normally EL range), but noise=High → DL
        result = analyzer.analyze(
            60.0, 70.0, _make_eval(final_score=60.0), _make_purpose(), feature_summary=features
        )
        assert result.recommended_approach == APPROACH_DEEP_LEARNING

    def test_high_noise_reasoning_mentions_noise(self):
        analyzer = FeasibilityAnalyzer()
        features = {"noise_level": "High"}
        result = analyzer.analyze(
            60.0, 70.0, _make_eval(final_score=60.0), _make_purpose(), feature_summary=features
        )
        assert "노이즈" in result.reasoning


# ------------------------------------------------------------------ #
#  12. Feature summary: moderate → EL bias                             #
# ------------------------------------------------------------------ #

class TestFeatureSummaryModerate:
    def test_medium_noise_biases_to_el(self):
        analyzer = FeasibilityAnalyzer()
        features = {"noise_level": "Medium", "edge_strength": 0.5, "contrast": 60}
        # gap = 5 (< 15), noise Medium → EL
        result = analyzer.analyze(
            65.0, 70.0, _make_eval(final_score=65.0), _make_purpose(), feature_summary=features
        )
        assert result.recommended_approach == APPROACH_EDGE_LEARNING


# ------------------------------------------------------------------ #
#  13. Missing / None feature_summary                                  #
# ------------------------------------------------------------------ #

class TestMissingFeatureSummary:
    def test_none_feature_summary(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(50.0, 70.0, _make_eval(final_score=50.0), _make_purpose(), None)
        assert isinstance(result, FeasibilityResult)

    def test_empty_dict_feature_summary(self):
        analyzer = FeasibilityAnalyzer()
        result = analyzer.analyze(
            50.0, 70.0, _make_eval(final_score=50.0), _make_purpose(), feature_summary={}
        )
        assert isinstance(result, FeasibilityResult)


# ------------------------------------------------------------------ #
#  14. Feature summary included in AI prompt                           #
# ------------------------------------------------------------------ #

class TestFeatureSummaryInPrompt:
    def test_feature_keys_in_prompt(self):
        provider = MagicMock()
        provider.analyze_safe.return_value = _ai_response_dl()
        analyzer = FeasibilityAnalyzer(ai_provider=provider)
        features = {"noise_level": "High", "edge_strength": 0.2, "contrast": 15, "blob_count": 12}

        analyzer.analyze(
            40.0, 70.0, _make_eval(final_score=40.0), _make_purpose(), feature_summary=features
        )

        prompt = provider.analyze_safe.call_args[0][0]
        assert "noise_level" in prompt
        assert "High" in prompt
        assert "blob_count" in prompt
        assert "12" in prompt


# ------------------------------------------------------------------ #
#  15. FP/FN in heuristic reasoning                                    #
# ------------------------------------------------------------------ #

class TestFPFNInReasoning:
    def test_fp_fn_mentioned(self):
        analyzer = FeasibilityAnalyzer()
        ev = _make_eval(final_score=50.0, fp_images=["a.png", "b.png"], fn_images=["c.png"])
        result = analyzer.analyze(50.0, 70.0, ev, _make_purpose())

        assert "FP 2건" in result.reasoning
        assert "FN 1건" in result.reasoning
