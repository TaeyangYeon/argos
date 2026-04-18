"""
Tests for Step 44: Result viewer 5-tab layout completion.

Tests cover:
- 5 tabs in correct order with Korean labels
- SummaryTab with full and partial aggregate data
- InspectionTab empty state and skeleton rendering
- FeasibilityTab empty state and skeleton rendering
- load_all dispatcher and null safety
"""

import pytest
from PyQt6.QtWidgets import QApplication

from ui.pages.result_page import ResultPage
from ui.pages.summary_tab import SummaryTab
from ui.pages.inspection_tab import InspectionTab
from ui.pages.feasibility_tab import FeasibilityTab
from ui.components.sidebar import PageID

# Real dataclass imports — NO MagicMock for these
from core.models import (
    InspectionPurpose,
    AlignResult,
    EvaluationResult,
    FeasibilityResult,
    OptimizationResult,
    FeatureAnalysisSummary,
)
from core.analyzers.feature_analyzer import FullFeatureAnalysis
from core.analyzers.histogram_analyzer import HistogramAnalysisResult
from core.analyzers.noise_analyzer import NoiseAnalysisResult
from core.analyzers.edge_analyzer import EdgeAnalysisResult
from core.analyzers.shape_analyzer import ShapeAnalysisResult
from core.inspection.candidate_generator import EngineCandidate
from core.inspection.blob_inspector import BlobInspectionEngine


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def result_page(qtbot):
    page = ResultPage()
    qtbot.addWidget(page)
    return page


@pytest.fixture
def inspection_purpose():
    return InspectionPurpose(
        inspection_type="결함검출",
        description="표면 스크래치 검사",
        ok_ng_criteria="스크래치 길이 1mm 이상 NG",
        target_feature="스크래치",
        measurement_unit="mm",
        tolerance="±0.1",
    )


@pytest.fixture
def feature_result():
    return FullFeatureAnalysis(
        image_path="/tmp/test.png",
        image_width=640,
        image_height=480,
        histogram=HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=40.0,
            min_gray=10,
            max_gray=245,
            dynamic_range=235,
            peak_count=2,
            distribution_type="bimodal",
            separation_score=65.0,
        ),
        noise=NoiseAnalysisResult(
            laplacian_variance=120.0,
            snr_db=25.0,
            noise_level="Low",
            recommended_filter="gaussian_blur",
            estimated_noise_std=5.0,
        ),
        edge=EdgeAnalysisResult(
            mean_edge_strength=45.0,
            max_edge_strength=200.0,
            edge_density=0.15,
            dominant_direction="horizontal",
            horizontal_ratio=0.6,
            vertical_ratio=0.3,
            canny_threshold_suggestion=(50, 150),
            is_suitable_for_caliper=True,
            caliper_direction_suggestion="horizontal",
        ),
        shape=ShapeAnalysisResult(
            blob_count=5,
            blobs=[],
            mean_blob_area=100.0,
            mean_circularity=0.8,
            has_circular_structure=True,
            detected_circles=[],
            contour_complexity=12.0,
            has_repeating_pattern=False,
            pattern_description="none",
        ),
        summary=FeatureAnalysisSummary(
            mean_gray=128.0,
            std_gray=40.0,
            noise_level="Low",
            edge_density=0.15,
            blob_count=5,
            has_circular_structure=True,
        ),
        ai_prompt="test prompt",
        ai_summary="AI 분석 요약 텍스트",
    )


@pytest.fixture
def align_result():
    return AlignResult(
        success=True,
        strategy_name="PatternAlign",
        score=0.92,
    )


@pytest.fixture
def best_candidate():
    return EngineCandidate(
        engine_class=BlobInspectionEngine,
        engine_name="Blob Inspector",
        priority=0.9,
        rationale="높은 blob 수로 적합",
        source="rule_based",
    )


@pytest.fixture
def best_evaluation():
    return EvaluationResult(
        best_strategy="blob",
        ok_pass_rate=0.95,
        ng_detect_rate=0.90,
        final_score=85.0,
        margin=20.0,
        is_margin_warning=False,
    )


@pytest.fixture
def optimization_result(best_candidate, best_evaluation):
    return OptimizationResult(
        best_candidate=best_candidate,
        best_evaluation=best_evaluation,
        all_results=[],
        optimization_log=["iteration 1 complete"],
    )


@pytest.fixture
def feasibility_result():
    return FeasibilityResult(
        rule_based_sufficient=True,
        recommended_approach="Rule-based",
        reasoning="Rule-based 알고리즘으로 충분한 성능 달성 가능합니다.",
        model_suggestion=None,
    )


@pytest.fixture
def full_aggregate(
    feature_result, align_result, optimization_result, feasibility_result, inspection_purpose
):
    return {
        "feature": feature_result,
        "align": align_result,
        "inspection": optimization_result,
        "evaluation": {
            "failure_result": None,
            "feasibility_result": feasibility_result,
        },
        "inspection_purpose": inspection_purpose,
    }


@pytest.fixture
def partial_aggregate(feature_result, align_result, inspection_purpose):
    """Aggregate without inspection or feasibility (NG=0 scenario)."""
    return {
        "feature": feature_result,
        "align": align_result,
        "inspection": None,
        "evaluation": None,
        "inspection_purpose": inspection_purpose,
    }


# ── Tests ───────────────────────────────────────────────────────────────────


class TestResultPageTabs:
    """Tests for 6-tab structure and ordering."""

    def test_result_page_has_five_tabs_in_order(self, result_page):
        """ResultPage must have exactly 6 tabs."""
        assert result_page._tab_widget.count() == 6

    def test_tab_labels_are_korean_as_specified(self, result_page):
        """Tab labels must be in Korean and match the spec order."""
        tw = result_page._tab_widget
        labels = [tw.tabText(i) for i in range(tw.count())]
        assert labels == [
            "요약",
            "Feature 분석",
            "Align 결과",
            "Inspection 결과",
            "Feasibility",
            "Failure 분석",
        ]


class TestSummaryTab:
    """Tests for the SummaryTab widget."""

    def test_summary_tab_renders_with_full_aggregate(self, qtbot, full_aggregate):
        """SummaryTab shows all four cards when full aggregate is provided."""
        tab = SummaryTab()
        qtbot.addWidget(tab)
        tab.load_data(full_aggregate)

        # 검사 목적 card shows inspection_type
        assert "결함검출" in tab._purpose_type_label.text()
        # 사용 전략 card shows align strategy
        assert "PatternAlign" in tab._align_strategy_label.text()
        # 사용 전략 card shows inspection best candidate
        assert "Blob Inspector" in tab._inspection_algo_label.text()
        # 최종 스코어 card shows align score
        assert "92.0" in tab._align_score_label.text()
        # 최종 스코어 card shows inspection score
        assert "85.0" in tab._inspection_score_label.text()
        # 최종 스코어 card shows feasibility level
        assert "Rule-based" in tab._feasibility_level_label.text()
        # 권장 접근법 card
        assert "Rule-based" in tab._approach_label.text()

    def test_summary_tab_renders_with_partial_aggregate(self, qtbot, partial_aggregate):
        """SummaryTab renders gracefully when inspection/feasibility are missing."""
        tab = SummaryTab()
        qtbot.addWidget(tab)
        tab.load_data(partial_aggregate)

        # Inspection algo should show N/A
        assert "N/A" in tab._inspection_algo_label.text()
        # Inspection score should show dash
        assert "—" in tab._inspection_score_label.text()
        # Feasibility level should show dash
        assert "—" in tab._feasibility_level_label.text()
        # Approach label should indicate missing feasibility
        assert "Feasibility 결과 없음" in tab._approach_label.text()


class TestInspectionTab:
    """Tests for the InspectionTab skeleton."""

    def test_inspection_tab_empty_state_when_no_inspection(self, qtbot):
        """InspectionTab shows Korean empty-state message when result is None."""
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(None)

        text = tab._content_label.text()
        assert "Inspection 결과 없음" in text

    def test_inspection_tab_skeleton_renders_best_candidate_name_and_score(
        self, qtbot, optimization_result
    ):
        """InspectionTab skeleton shows best candidate name and score."""
        tab = InspectionTab()
        qtbot.addWidget(tab)
        tab.load_data(optimization_result)

        assert "Blob Inspector" in tab._algo_name_label.text()
        assert "85.0" in tab._score_label.text()


class TestFeasibilityTab:
    """Tests for the FeasibilityTab skeleton."""

    def test_feasibility_tab_empty_state_when_no_feasibility(self, qtbot):
        """FeasibilityTab shows Korean empty-state when result is None."""
        tab = FeasibilityTab()
        qtbot.addWidget(tab)
        tab.load_data(None)

        text = tab._content_label.text()
        assert "Feasibility 결과 없음" in text

    def test_feasibility_tab_skeleton_renders_level_badge(self, qtbot, feasibility_result):
        """FeasibilityTab skeleton shows the level badge text."""
        tab = FeasibilityTab()
        qtbot.addWidget(tab)
        tab.load_data(feasibility_result)

        assert "Rule-based" in tab._level_badge.text()
        assert tab._rationale_label.text() != ""


class TestLoadAll:
    """Tests for ResultPage.load_all dispatcher."""

    def test_load_all_dispatches_to_each_tab(self, result_page, full_aggregate):
        """load_all fills all tabs without error."""
        result_page.load_all(full_aggregate)

        # Summary tab should have been populated
        assert "결함검출" in result_page._summary_tab._purpose_type_label.text()
        # Inspection tab should have been populated
        assert "Blob Inspector" in result_page._inspection_tab._algo_name_label.text()
        # Feasibility tab should have been populated
        assert "Rule-based" in result_page._feasibility_tab._level_badge.text()

    def test_load_all_is_null_safe_on_missing_sections(self, result_page, partial_aggregate):
        """load_all must not raise even when inspection/evaluation are None."""
        # Must not raise
        result_page.load_all(partial_aggregate)

        # Inspection tab shows empty state
        assert "Inspection 결과 없음" in result_page._inspection_tab._content_label.text()
        # Feasibility tab shows empty state
        assert "Feasibility 결과 없음" in result_page._feasibility_tab._content_label.text()
