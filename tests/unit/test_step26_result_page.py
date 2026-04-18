"""
Tests for Step 26: Feature Analysis result viewer UI.

This module tests the ResultPage implementation with comprehensive
feature analysis display and tab switching functionality.
"""

import pytest
from unittest.mock import Mock
from PyQt6.QtWidgets import QApplication, QProgressBar
from PyQt6.QtCore import Qt

from ui.pages.result_page import ResultPage, FeatureTab
from ui.components.sidebar import PageID
from core.analyzers.feature_analyzer import FullFeatureAnalysis
from core.analyzers.histogram_analyzer import HistogramAnalysisResult
from core.analyzers.noise_analyzer import NoiseAnalysisResult
from core.analyzers.edge_analyzer import EdgeAnalysisResult
from core.analyzers.shape_analyzer import ShapeAnalysisResult
from core.models import FeatureAnalysisSummary


class TestResultPage:
    """Test suite for ResultPage UI component."""
    
    @pytest.fixture
    def result_page(self, qtbot):
        """Create a ResultPage instance for testing."""
        page = ResultPage()
        qtbot.addWidget(page)
        return page
    
    def test_result_page_created(self, result_page):
        """Test that ResultPage instantiates without error."""
        assert result_page is not None
        assert result_page.page_id == PageID.RESULTS
        assert result_page.title == "결과 보기"
        
    def test_tab_widget_created(self, result_page):
        """Test that tab widget is properly created with all tabs."""
        tab_widget = result_page._tab_widget
        assert tab_widget is not None
        assert tab_widget.count() == 6

        # Check tab titles
        expected_tabs = ["요약", "Feature 분석", "Align 결과", "Inspection 결과", "Feasibility", "Failure 분석"]
        actual_tabs = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        assert actual_tabs == expected_tabs
        
    def test_feature_tab_accessible(self, result_page):
        """Test that feature tab is accessible and properly initialized."""
        feature_tab = result_page._feature_tab
        assert isinstance(feature_tab, FeatureTab)
        assert feature_tab is not None


class TestFeatureTab:
    """Test suite for FeatureTab UI component."""
    
    @pytest.fixture
    def feature_tab(self, qtbot):
        """Create a FeatureTab instance for testing."""
        tab = FeatureTab()
        qtbot.addWidget(tab)
        return tab
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Create a mock FullFeatureAnalysis for testing."""
        # Create mock sub-results
        histogram_result = HistogramAnalysisResult(
            mean_gray=128.5,
            std_gray=45.2,
            min_gray=10,
            max_gray=250,
            dynamic_range=240,
            peak_count=2,
            distribution_type="bimodal",
            separation_score=75.0
        )
        
        noise_result = NoiseAnalysisResult(
            laplacian_variance=150.5,
            snr_db=25.8,
            noise_level="HIGH",
            recommended_filter="gaussian_blur",
            estimated_noise_std=12.3
        )
        
        edge_result = EdgeAnalysisResult(
            mean_edge_strength=85.2,
            max_edge_strength=255.0,
            edge_density=0.1234,
            dominant_direction="horizontal",
            horizontal_ratio=0.6,
            vertical_ratio=0.4,
            canny_threshold_suggestion=(50, 150),
            is_suitable_for_caliper=True,
            caliper_direction_suggestion="horizontal"
        )
        
        shape_result = ShapeAnalysisResult(
            blob_count=15,
            blobs=[],
            mean_blob_area=250.0,
            mean_circularity=0.8,
            has_circular_structure=True,
            detected_circles=[],
            contour_complexity=0.65,
            has_repeating_pattern=False,
            pattern_description="테스트용 패턴 설명"
        )
        
        summary = FeatureAnalysisSummary(
            mean_gray=128.5,
            std_gray=45.2,
            noise_level="HIGH",
            edge_density=0.1234,
            blob_count=15,
            has_circular_structure=True,
            ai_summary="테스트용 AI 분석 결과입니다."
        )
        
        return FullFeatureAnalysis(
            image_path="/test/path/image.png",
            image_width=640,
            image_height=480,
            histogram=histogram_result,
            noise=noise_result,
            edge=edge_result,
            shape=shape_result,
            summary=summary,
            ai_prompt="Test AI prompt",
            ai_summary="테스트용 AI 분석 결과입니다.",
            preprocessing_recommendations=[
                "노이즈 제거 권장: gaussian_blur",
                "에지 약함 - 언샵 마스크 또는 에지 강화 권장"
            ]
        )
    
    def test_feature_tab_renders_with_data(self, feature_tab, mock_analysis_result):
        """Test that load_data() populates fields correctly with mock data."""
        # Load test data
        feature_tab.load_data(mock_analysis_result)
        
        # Check histogram stats are updated
        assert "128.5" in feature_tab._mean_label.text()
        assert "45.2" in feature_tab._std_label.text()
        assert "240" in feature_tab._range_label.text()
        
        # Check noise badge is updated
        assert "HIGH" in feature_tab._noise_badge.text()
        
        # Check edge stats are updated
        assert "85.2" in feature_tab._edge_strength_label.text()
        assert "0.1234" in feature_tab._edge_density_label.text()
        
        # Check caliper suitability
        assert "적합" in feature_tab._caliper_badge.text()
        
        # Check shape analysis
        assert "15" in feature_tab._blob_count_label.text()
        assert "있음" in feature_tab._circular_flag.text()
    
    def test_ai_summary_displayed(self, feature_tab, mock_analysis_result):
        """Test that AI summary text appears in the text area."""
        feature_tab.load_data(mock_analysis_result)
        
        ai_text = feature_tab._ai_summary_text.toPlainText()
        assert "테스트용 AI 분석 결과입니다." in ai_text
    
    def test_noise_badge_color_high(self, feature_tab, mock_analysis_result):
        """Test that HIGH noise level shows red badge."""
        feature_tab.load_data(mock_analysis_result)
        
        # Check that noise badge text contains HIGH or 높음
        badge_text = feature_tab._noise_badge.text()
        assert "HIGH" in badge_text
        
        # Check that badge style includes red color
        badge_style = feature_tab._noise_badge.styleSheet()
        assert "#F44336" in badge_style  # Red color for HIGH noise
    
    def test_noise_badge_color_medium(self, feature_tab, mock_analysis_result):
        """Test that MEDIUM noise level shows orange badge."""
        # Modify mock data to have MEDIUM noise
        mock_analysis_result.noise.noise_level = "MEDIUM"
        feature_tab.load_data(mock_analysis_result)
        
        badge_text = feature_tab._noise_badge.text()
        assert "MEDIUM" in badge_text
        
        badge_style = feature_tab._noise_badge.styleSheet()
        assert "#FF9800" in badge_style  # Orange color for MEDIUM noise
    
    def test_noise_badge_color_low(self, feature_tab, mock_analysis_result):
        """Test that LOW noise level shows green badge."""
        # Modify mock data to have LOW noise
        mock_analysis_result.noise.noise_level = "LOW"
        feature_tab.load_data(mock_analysis_result)
        
        badge_text = feature_tab._noise_badge.text()
        assert "LOW" in badge_text
        
        badge_style = feature_tab._noise_badge.styleSheet()
        assert "#4CAF50" in badge_style  # Green color for LOW noise
    
    def test_separation_score_bar(self, feature_tab, mock_analysis_result):
        """Test that separation_score=75 sets QProgressBar value to 75."""
        feature_tab.load_data(mock_analysis_result)
        
        progress_value = feature_tab._separation_progress.value()
        assert progress_value == 75
    
    def test_separation_score_no_data(self, feature_tab, mock_analysis_result):
        """Test that missing separation_score sets progress bar to 0."""
        # Remove separation_score
        mock_analysis_result.histogram.separation_score = None
        feature_tab.load_data(mock_analysis_result)
        
        progress_value = feature_tab._separation_progress.value()
        assert progress_value == 0
    
    def test_caliper_suitable_badge(self, feature_tab, mock_analysis_result):
        """Test caliper suitability badge for suitable edge."""
        feature_tab.load_data(mock_analysis_result)
        
        badge_text = feature_tab._caliper_badge.text()
        assert "적합" in badge_text
        
        badge_style = feature_tab._caliper_badge.styleSheet()
        assert "#1E88E5" in badge_style  # Blue color for suitable
    
    def test_caliper_unsuitable_badge(self, feature_tab, mock_analysis_result):
        """Test caliper suitability badge for unsuitable edge."""
        # Modify mock data to be unsuitable for caliper
        mock_analysis_result.edge.is_suitable_for_caliper = False
        feature_tab.load_data(mock_analysis_result)
        
        badge_text = feature_tab._caliper_badge.text()
        assert "부적합" in badge_text
        
        badge_style = feature_tab._caliper_badge.styleSheet()
        assert "#424242" in badge_style  # Gray color for unsuitable
    
    def test_preprocessing_recommendations_list(self, feature_tab, mock_analysis_result):
        """Test that preprocessing recommendations are displayed in list."""
        feature_tab.load_data(mock_analysis_result)
        
        recommendations_list = feature_tab._recommendations_list
        assert recommendations_list.count() == 2
        
        # Check recommendation texts
        item1 = recommendations_list.item(0)
        item2 = recommendations_list.item(1)
        
        assert "노이즈 제거 권장" in item1.text()
        assert "에지 약함" in item2.text()
    
    def test_circular_structure_present(self, feature_tab, mock_analysis_result):
        """Test circular structure flag when structure is present."""
        feature_tab.load_data(mock_analysis_result)
        
        circular_text = feature_tab._circular_flag.text()
        assert "있음" in circular_text
    
    def test_circular_structure_absent(self, feature_tab, mock_analysis_result):
        """Test circular structure flag when structure is absent."""
        # Modify mock data to have no circular structure
        mock_analysis_result.shape.has_circular_structure = False
        feature_tab.load_data(mock_analysis_result)
        
        circular_text = feature_tab._circular_flag.text()
        assert "없음" in circular_text


class TestResultPageIntegration:
    """Integration tests for ResultPage with FeatureTab."""
    
    @pytest.fixture
    def result_page(self, qtbot):
        """Create a ResultPage instance for testing."""
        page = ResultPage()
        qtbot.addWidget(page)
        return page
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Create a mock FullFeatureAnalysis for testing."""
        histogram_result = HistogramAnalysisResult(
            mean_gray=100.0,
            std_gray=30.0,
            min_gray=0,
            max_gray=255,
            dynamic_range=255,
            peak_count=1,
            distribution_type="unimodal",
            separation_score=50.0
        )
        
        noise_result = NoiseAnalysisResult(
            laplacian_variance=100.0,
            snr_db=20.0,
            noise_level="MEDIUM",
            recommended_filter="median_blur",
            estimated_noise_std=10.0
        )
        
        edge_result = EdgeAnalysisResult(
            mean_edge_strength=60.0,
            max_edge_strength=200.0,
            edge_density=0.0800,
            dominant_direction="vertical",
            horizontal_ratio=0.3,
            vertical_ratio=0.7,
            canny_threshold_suggestion=(30, 100),
            is_suitable_for_caliper=False,
            caliper_direction_suggestion="vertical"
        )
        
        shape_result = ShapeAnalysisResult(
            blob_count=5,
            blobs=[],
            mean_blob_area=150.0,
            mean_circularity=0.5,
            has_circular_structure=False,
            detected_circles=[],
            contour_complexity=0.4,
            has_repeating_pattern=True,
            pattern_description="통합 테스트용 패턴 설명"
        )
        
        summary = FeatureAnalysisSummary(
            mean_gray=100.0,
            std_gray=30.0,
            noise_level="MEDIUM",
            edge_density=0.0800,
            blob_count=5,
            has_circular_structure=False,
            ai_summary="통합 테스트용 AI 분석입니다."
        )
        
        return FullFeatureAnalysis(
            image_path="/test/integration/image.png",
            image_width=800,
            image_height=600,
            histogram=histogram_result,
            noise=noise_result,
            edge=edge_result,
            shape=shape_result,
            summary=summary,
            ai_prompt="Integration test prompt",
            ai_summary="통합 테스트용 AI 분석입니다.",
            preprocessing_recommendations=[
                "보통 수준 노이즈 - 필터링 고려",
                "현재 이미지 품질 양호 - 추가 전처리 불필요"
            ]
        )
    
    def test_tab_switches_to_feature_on_load(self, result_page, mock_analysis_result):
        """Test that after load_result(), current tab index is the 이미지 특성 tab."""
        # Initially should be on first tab (index 0)
        initial_index = result_page._tab_widget.currentIndex()
        assert initial_index == 0
        
        # Load result should switch to feature tab (index 1)
        result_page.load_result(mock_analysis_result)
        
        # Process the deferred Qt timer event
        result_page._apply_result()
        
        current_index = result_page._tab_widget.currentIndex()
        assert current_index == 1  # "이미지 특성" tab
    
    def test_load_result_populates_feature_tab(self, result_page, mock_analysis_result):
        """Test that load_result() properly populates the feature tab with data."""
        result_page.load_result(mock_analysis_result)
        
        # Process the deferred Qt timer event
        result_page._apply_result()
        
        feature_tab = result_page._feature_tab
        
        # Verify data is loaded in feature tab
        assert "100.0" in feature_tab._mean_label.text()
        assert "MEDIUM" in feature_tab._noise_badge.text()
        assert "부적합" in feature_tab._caliper_badge.text()
        assert "5" in feature_tab._blob_count_label.text()
        assert "없음" in feature_tab._circular_flag.text()
        
        # Verify separation score
        assert feature_tab._separation_progress.value() == 50
        
        # Verify AI summary
        ai_text = feature_tab._ai_summary_text.toPlainText()
        assert "통합 테스트용 AI 분석입니다." in ai_text
        
        # Verify recommendations
        assert feature_tab._recommendations_list.count() == 2