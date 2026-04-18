"""
Step 47 — FeasibilityTab 전체 구현 테스트.

기술 수준 배지, 점수 상세, AI 판단 근거, 추천 모델, Feature 요약,
의사결정 흐름도 검증.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

from core.models import FeasibilityResult
from ui.pages.feasibility_tab import (
    FeasibilityTab,
    _BADGE_COLORS,
    _BADGE_SUBTITLES,
    _EMPTY_MSG,
)

# ── Ensure QApplication exists ───────────────────────────────────────────────

_app = QApplication.instance() or QApplication([])


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def tab():
    """Create and show a FeasibilityTab so isVisible() works."""
    t = FeasibilityTab()
    t.show()
    return t


def _make_result(
    rule_based_sufficient: bool = True,
    recommended_approach: str = "Rule-based",
    reasoning: str = "Test reasoning",
    model_suggestion: str | None = None,
) -> FeasibilityResult:
    return FeasibilityResult(
        rule_based_sufficient=rule_based_sufficient,
        recommended_approach=recommended_approach,
        reasoning=reasoning,
        model_suggestion=model_suggestion,
    )


def _rb_result() -> FeasibilityResult:
    return _make_result(
        rule_based_sufficient=True,
        recommended_approach="Rule-based",
        reasoning="Rule-based 검사로 충분합니다. 최고 점수 85.0이(가) 임계값 70.0을(를) 15.0점 초과했습니다.",
    )


def _el_result() -> FeasibilityResult:
    return _make_result(
        rule_based_sufficient=False,
        recommended_approach="Edge Learning",
        reasoning="Edge Learning이 적합합니다. 점수 갭 20점.",
        model_suggestion="MobileNet-based classifier",
    )


def _dl_result() -> FeasibilityResult:
    return _make_result(
        rule_based_sufficient=False,
        recommended_approach="Deep Learning",
        reasoning="Deep Learning이 필요합니다. 노이즈가 높고 점수 갭이 큽니다.",
        model_suggestion="Anomaly detection (PaDiM/PatchCore), ResNet CNN",
    )


def _default_context() -> dict:
    return {"best_score": 85.0, "threshold": 70.0}


def _low_score_context() -> dict:
    return {"best_score": 45.0, "threshold": 70.0}


# ── Tests ────────────────────────────────────────────────────────────────────


class TestFeasibilityTabCreation:
    """Widget creation and initial empty state tests."""

    def test_creates_widget(self, tab):
        assert tab is not None

    def test_initial_empty_state(self, tab):
        assert tab._empty_label.isVisible()
        assert tab._empty_label.text() == _EMPTY_MSG

    def test_sections_hidden_initially(self, tab):
        assert not tab._badge_card.isVisible()
        assert not tab._score_card.isVisible()
        assert not tab._rationale_card.isVisible()
        assert not tab._models_card.isVisible()
        assert not tab._feature_card.isVisible()
        assert not tab._flow_card.isVisible()


class TestLoadRuleBased:
    """Tests for RULE_BASED level data."""

    def test_loads_rule_based_result(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert not tab._empty_label.isVisible()
        assert tab._badge_card.isVisible()

    def test_badge_shows_rule_based(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert tab._level_badge.text() == "Rule-based"

    def test_badge_color_rule_based(self, tab):
        tab.load_data(_rb_result(), _default_context())
        style = tab._level_badge.styleSheet()
        assert _BADGE_COLORS["Rule-based"] in style

    def test_subtitle_rule_based(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert tab._level_subtitle.text() == _BADGE_SUBTITLES["Rule-based"]

    def test_models_hidden_for_rule_based(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert not tab._models_card.isVisible()

    def test_flow_rule_based_path_highlighted(self, tab):
        tab.load_data(_rb_result(), _default_context())
        step_rb = tab._flow_step_labels["step_rule_based"]
        assert "Rule-based 충분 ✓" in step_rb.text()
        assert "#4CAF50" in step_rb.styleSheet()


class TestLoadEdgeLearning:
    """Tests for EDGE_LEARNING level data."""

    def test_loads_el_result(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert tab._badge_card.isVisible()

    def test_badge_color_el(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        style = tab._level_badge.styleSheet()
        assert _BADGE_COLORS["Edge Learning"] in style

    def test_badge_text_el(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert tab._level_badge.text() == "Edge Learning"

    def test_models_visible_for_el(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert tab._models_card.isVisible()
        assert tab._models_table.rowCount() > 0

    def test_flow_el_path_highlighted(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        step_el = tab._flow_step_labels["step_el"]
        assert "Edge Learning 선택 ✓" in step_el.text()
        assert "#FFA726" in step_el.styleSheet()


class TestLoadDeepLearning:
    """Tests for DEEP_LEARNING level data."""

    def test_loads_dl_result(self, tab):
        tab.load_data(_dl_result(), _low_score_context())
        assert tab._badge_card.isVisible()

    def test_badge_color_dl(self, tab):
        tab.load_data(_dl_result(), _low_score_context())
        style = tab._level_badge.styleSheet()
        assert _BADGE_COLORS["Deep Learning"] in style

    def test_badge_text_dl(self, tab):
        tab.load_data(_dl_result(), _low_score_context())
        assert tab._level_badge.text() == "Deep Learning"

    def test_models_visible_for_dl(self, tab):
        tab.load_data(_dl_result(), _low_score_context())
        assert tab._models_card.isVisible()

    def test_models_table_multiple_entries(self, tab):
        """DL result has comma-separated suggestions — should produce multiple rows."""
        tab.load_data(_dl_result(), _low_score_context())
        # 1 row for approach + 2 rows for models (split by comma)
        assert tab._models_table.rowCount() == 3

    def test_flow_dl_path_highlighted(self, tab):
        tab.load_data(_dl_result(), _low_score_context())
        step_dl = tab._flow_step_labels["step_dl"]
        assert "Deep Learning 선택 ✓" in step_dl.text()
        assert "#EF5350" in step_dl.styleSheet()


class TestScoreBar:
    """Score bar visualization tests."""

    def test_score_bar_visible_with_context(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert tab._score_bar_frame.isVisible()

    def test_score_bar_value(self, tab):
        tab.load_data(_rb_result(), {"best_score": 85.0, "threshold": 70.0})
        assert tab._score_bar.value() == 85

    def test_score_bar_hidden_without_context(self, tab):
        tab.load_data(_rb_result())  # No context
        assert not tab._score_bar_frame.isVisible()

    def test_threshold_marker_text(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert "70.0" in tab._threshold_marker.text()


class TestScoreDetails:
    """Score details card tests."""

    def test_best_score_display(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert tab._best_score_label.text() == "85.0"

    def test_threshold_display(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert tab._threshold_label.text() == "70.0"

    def test_gap_positive(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert tab._gap_label.text() == "+15.0"

    def test_gap_negative(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert tab._gap_label.text() == "-25.0"

    def test_interpretation_positive(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert "초과" in tab._score_interpretation.text()

    def test_interpretation_negative(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert "미달" in tab._score_interpretation.text()

    def test_score_without_context(self, tab):
        tab.load_data(_rb_result())
        assert tab._best_score_label.text() == "—"
        assert tab._threshold_label.text() == "—"
        assert tab._gap_label.text() == "—"


class TestRationale:
    """AI rationale card tests."""

    def test_rationale_displayed(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert "Edge Learning" in tab._rationale_text.text()

    def test_rationale_empty_fallback(self, tab):
        result = _make_result(reasoning="")
        tab.load_data(result)
        assert tab._rationale_text.text() == "판단 근거 정보 없음"


class TestFeatureSummary:
    """Feature summary card tests."""

    def test_feature_summary_displayed(self, tab):
        ctx = {
            "best_score": 45.0,
            "threshold": 70.0,
            "feature_summary": {
                "noise_level": "Medium",
                "edge_strength": 42.5,
                "contrast": 128,
            },
        }
        tab.load_data(_el_result(), ctx)
        assert len(tab._feature_rows) == 3

    def test_feature_empty_without_data(self, tab):
        tab.load_data(_rb_result())
        assert tab._feature_empty_label.isVisible()

    def test_feature_empty_with_none(self, tab):
        tab.load_data(_rb_result(), {"feature_summary": None})
        assert tab._feature_empty_label.isVisible()


class TestEdgeCases:
    """Edge cases: empty dict, missing keys, None values."""

    def test_load_none_result(self, tab):
        tab.load_data(None)
        assert tab._empty_label.isVisible()
        assert not tab._badge_card.isVisible()

    def test_load_empty_context(self, tab):
        tab.load_data(_rb_result(), {})
        assert tab._badge_card.isVisible()
        assert not tab._score_bar_frame.isVisible()

    def test_mock_object_with_missing_attrs(self, tab):
        """Result object with missing attributes should not crash."""
        mock_result = MagicMock(spec=[])
        mock_result.recommended_approach = "Rule-based"
        mock_result.reasoning = "Test"
        mock_result.model_suggestion = None
        mock_result.rule_based_sufficient = True
        tab.load_data(mock_result)
        assert tab._badge_card.isVisible()

    def test_empty_feature_summary_dict(self, tab):
        tab.load_data(_rb_result(), {"feature_summary": {}})
        assert tab._feature_empty_label.isVisible()


class TestClearResult:
    """Clear result resets all widgets."""

    def test_clear_after_load(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        assert tab._badge_card.isVisible()

        tab.clear_result()
        assert tab._empty_label.isVisible()
        assert not tab._badge_card.isVisible()
        assert not tab._score_card.isVisible()
        assert not tab._rationale_card.isVisible()
        assert not tab._models_card.isVisible()
        assert not tab._feature_card.isVisible()
        assert not tab._flow_card.isVisible()

    def test_clear_on_initial_state(self, tab):
        tab.clear_result()
        assert tab._empty_label.isVisible()


class TestDecisionFlow:
    """Decision flow diagram highlighting tests."""

    def test_score_check_always_active(self, tab):
        tab.load_data(_rb_result(), _default_context())
        style = tab._flow_step_labels["step_score_check"].styleSheet()
        assert "#1E88E5" in style

    def test_rule_based_inactive_steps(self, tab):
        tab.load_data(_rb_result(), _default_context())
        assert "불필요" in tab._flow_step_labels["step_ai_decision"].text()

    def test_el_inactive_dl(self, tab):
        tab.load_data(_el_result(), _low_score_context())
        dl_style = tab._flow_step_labels["step_dl"].styleSheet()
        # DL should be inactive (dimmed)
        assert "#616161" in dl_style

    def test_dl_inactive_el(self, tab):
        tab.load_data(_dl_result(), _low_score_context())
        el_style = tab._flow_step_labels["step_el"].styleSheet()
        assert "#616161" in el_style

    def test_flow_with_score_context(self, tab):
        tab.load_data(_rb_result(), _default_context())
        text = tab._flow_step_labels["step_score_check"].text()
        assert "85.0" in text
        assert "70.0" in text
