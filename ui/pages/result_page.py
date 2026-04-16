"""Results viewing page for the Argos vision algorithm design application.

This module provides the interface for viewing analysis results,
algorithm parameters, and performance metrics.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QWidget, QScrollArea,
    QTextEdit, QProgressBar, QFrame, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from .base_page import BasePage, PageHeader
from .align_tab import AlignTab
from .summary_tab import SummaryTab
from .inspection_tab import InspectionTab
from .feasibility_tab import FeasibilityTab
from ui.components.sidebar import PageID
from core.analyzers.feature_analyzer import FullFeatureAnalysis


class FeatureTab(QWidget):
    """
    Feature analysis tab showing comprehensive image analysis results.
    """
    
    def __init__(self, parent=None):
        """Initialize the feature analysis tab."""
        self._mean_label = None
        self._std_label = None
        self._range_label = None
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Setup the feature tab UI."""
        # Main scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Main content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        
        # Histogram stats section
        histogram_section = self._create_histogram_section()
        content_layout.addWidget(histogram_section)
        
        # Noise and edge analysis section
        analysis_section = self._create_analysis_section()
        content_layout.addWidget(analysis_section)
        
        # Shape and blob analysis section
        shape_section = self._create_shape_section()
        content_layout.addWidget(shape_section)
        
        # OK/NG separation section
        separation_section = self._create_separation_section()
        content_layout.addWidget(separation_section)
        
        # AI analysis section
        ai_section = self._create_ai_section()
        content_layout.addWidget(ai_section)
        
        # Preprocessing recommendations section
        recommendations_section = self._create_recommendations_section()
        content_layout.addWidget(recommendations_section)
        
        # Add stretch at bottom
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)
        
    def _create_histogram_section(self) -> QWidget:
        """Create histogram statistics section."""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("히스토그램 특성")
        title.setStyleSheet("color: #E0E0E0; font-size: 16px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        
        # Stats container with plain labels
        stats_layout = QHBoxLayout()
        
        # Plain QLabel widgets instead of StatCard
        self._mean_container = self._create_stat_label_group("평균 밝기", "0-255 범위")
        self._std_container = self._create_stat_label_group("표준편차", "분산도 측정")
        self._range_container = self._create_stat_label_group("동적 범위", "대비 수준")
        
        stats_layout.addWidget(self._mean_container)
        stats_layout.addWidget(self._std_container)
        stats_layout.addWidget(self._range_container)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        return section
    
    def _create_stat_label_group(self, title: str, subtitle: str) -> QFrame:
        """Create a simple stat display group with plain QLabels."""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #1E2A4A;
                border: 1px solid #2A2A4A;
                border-left: 4px solid #1E88E5;
                border-radius: 8px;
                min-width: 180px;
            }
        """)
        container.setContentsMargins(12, 12, 12, 12)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        
        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #9E9E9E; font-size: 12px;")
        layout.addWidget(title_label)
        
        # Value label (store reference for updates)
        value_label = QLabel("—")
        value_label.setStyleSheet("color: #1E88E5; font-size: 28px; font-weight: bold;")
        layout.addWidget(value_label)
        
        # Subtitle label
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #616161; font-size: 11px;")
        layout.addWidget(subtitle_label)
        
        # Store the value label for easy access
        if title == "평균 밝기":
            self._mean_label = value_label
        elif title == "표준편차":
            self._std_label = value_label
        elif title == "동적 범위":
            self._range_label = value_label
        
        return container
        
    def _create_analysis_section(self) -> QWidget:
        """Create noise and edge analysis section."""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("노이즈 및 에지 분석")
        title.setStyleSheet("color: #E0E0E0; font-size: 16px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        
        # Analysis content
        content_layout = QHBoxLayout()
        
        # Noise level badge
        self._noise_badge = QLabel("노이즈: --")
        self._noise_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._noise_badge.setFixedHeight(40)
        self._noise_badge.setStyleSheet("""
            QLabel {
                background-color: #424242;
                color: #E0E0E0;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }
        """)
        content_layout.addWidget(self._noise_badge)
        
        # Edge stats
        edge_layout = QVBoxLayout()
        
        self._edge_strength_label = QLabel("에지 강도: --")
        self._edge_strength_label.setStyleSheet("color: #E0E0E0;")
        edge_layout.addWidget(self._edge_strength_label)
        
        self._edge_density_label = QLabel("에지 밀도: --")
        self._edge_density_label.setStyleSheet("color: #E0E0E0;")
        edge_layout.addWidget(self._edge_density_label)
        
        content_layout.addLayout(edge_layout)
        
        # Caliper suitability badge
        self._caliper_badge = QLabel("캘리퍼: --")
        self._caliper_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._caliper_badge.setFixedHeight(40)
        self._caliper_badge.setStyleSheet("""
            QLabel {
                background-color: #424242;
                color: #E0E0E0;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }
        """)
        content_layout.addWidget(self._caliper_badge)
        
        content_layout.addStretch()
        
        layout.addLayout(content_layout)
        
        return section
        
    def _create_shape_section(self) -> QWidget:
        """Create shape analysis section."""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("형상 및 Blob 분석")
        title.setStyleSheet("color: #E0E0E0; font-size: 16px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        
        # Shape content
        content_layout = QHBoxLayout()
        
        # Blob count
        self._blob_count_label = QLabel("Blob 수: --")
        self._blob_count_label.setStyleSheet("color: #E0E0E0; font-size: 14px;")
        content_layout.addWidget(self._blob_count_label)
        
        # Circular structure flag
        self._circular_flag = QLabel("원형 구조: --")
        self._circular_flag.setStyleSheet("color: #E0E0E0; font-size: 14px;")
        content_layout.addWidget(self._circular_flag)
        
        content_layout.addStretch()
        
        layout.addLayout(content_layout)
        
        return section
        
    def _create_separation_section(self) -> QWidget:
        """Create OK/NG separation section."""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("OK/NG 분리도")
        title.setStyleSheet("color: #E0E0E0; font-size: 16px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        
        # Progress bar for separation score
        self._separation_progress = QProgressBar()
        self._separation_progress.setRange(0, 100)
        self._separation_progress.setValue(0)
        self._separation_progress.setFixedHeight(30)
        self._separation_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2A2A4A;
                border-radius: 15px;
                background-color: #1A1A2E;
                text-align: center;
                color: #E0E0E0;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #1E88E5;
                border-radius: 13px;
            }
        """)
        layout.addWidget(self._separation_progress)
        
        return section
        
    def _create_ai_section(self) -> QWidget:
        """Create AI analysis section."""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("AI 분석 요약")
        title.setStyleSheet("color: #E0E0E0; font-size: 16px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        
        # AI summary text area
        self._ai_summary_text = QTextEdit()
        self._ai_summary_text.setReadOnly(True)
        self._ai_summary_text.setFixedHeight(120)
        self._ai_summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #1A1A2E;
                border: 1px solid #2A2A4A;
                border-radius: 6px;
                color: #E0E0E0;
                padding: 12px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self._ai_summary_text)
        
        return section
        
    def _create_recommendations_section(self) -> QWidget:
        """Create preprocessing recommendations section."""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("전처리 권장사항")
        title.setStyleSheet("color: #E0E0E0; font-size: 16px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        
        # Recommendations list
        self._recommendations_list = QListWidget()
        self._recommendations_list.setFixedHeight(120)
        self._recommendations_list.setStyleSheet("""
            QListWidget {
                background-color: #1A1A2E;
                border: 1px solid #2A2A4A;
                border-radius: 6px;
                color: #E0E0E0;
                padding: 8px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #2A2A4A;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        layout.addWidget(self._recommendations_list)
        
        return section
        
    def load_data(self, result: FullFeatureAnalysis) -> None:
        """Load feature analysis data into the UI."""
        # Update histogram stats with defensive access
        histogram = getattr(result, 'histogram', None)
        mean_gray = getattr(histogram, 'mean_gray', None) if histogram else None
        std_gray = getattr(histogram, 'std_gray', None) if histogram else None
        dynamic_range = getattr(histogram, 'dynamic_range', None) if histogram else None
        
        # Format values for display
        mean_value = f"{mean_gray:.1f}" if mean_gray is not None else "—"
        std_value = f"{std_gray:.1f}" if std_gray is not None else "—"
        range_value = str(dynamic_range) if dynamic_range is not None else "—"
        
        # Update histogram QLabel widgets directly
        # self._mean_label.setText(mean_value)
        # self._std_label.setText(std_value)
        # self._range_label.setText(range_value)
        if self._mean_label:
            self._mean_label.setText(mean_value)
        if self._std_label:
            self._std_label.setText(std_value)
        if self._range_label:
            self._range_label.setText(range_value)
        
        # Update noise level badge with case normalization
        noise_level = getattr(result.noise, 'noise_level', 'Low')
        noise_level_upper = str(noise_level).upper()
        self._noise_badge.setText(f"노이즈: {noise_level}")
        
        # Set badge color based on noise level (normalized to uppercase)
        if noise_level_upper == "HIGH":
            badge_color = "#F44336"  # Red
        elif noise_level_upper == "MEDIUM":
            badge_color = "#FF9800"  # Orange
        else:
            badge_color = "#4CAF50"  # Green
            
        self._noise_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_color};
                color: #FFFFFF;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }}
        """)
        
        # Update edge stats with defensive access
        edge_strength = getattr(result.edge, 'mean_edge_strength', None)
        edge_density = getattr(result.edge, 'edge_density', None)
        
        self._edge_strength_label.setText(f"에지 강도: {edge_strength:.1f}" if edge_strength is not None else "에지 강도: —")
        self._edge_density_label.setText(f"에지 밀도: {edge_density:.4f}" if edge_density is not None else "에지 밀도: —")
        
        # Update caliper suitability badge with defensive access
        caliper_suitable = getattr(result.edge, 'is_suitable_for_caliper', False)
        self._caliper_badge.setText("캘리퍼: 적합" if caliper_suitable else "캘리퍼: 부적합")
        caliper_color = "#1E88E5" if caliper_suitable else "#424242"
        self._caliper_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {caliper_color};
                color: #FFFFFF;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }}
        """)
        
        # Update shape analysis with defensive access
        blob_count = getattr(result.shape, 'blob_count', 0)
        has_circular = getattr(result.shape, 'has_circular_structure', False)
        
        self._blob_count_label.setText(f"Blob 수: {blob_count}")
        circular_text = "있음" if has_circular else "없음"
        self._circular_flag.setText(f"원형 구조: {circular_text}")
        
        # Update separation score with safe fallback and tooltip for no NG case
        separation_score = getattr(result.histogram, 'separation_score', None)
        if separation_score is not None:
            try:
                score = int(float(separation_score))
                self._separation_progress.setValue(score)
                self._separation_progress.setToolTip(f"분리도: {float(separation_score):.1f}%")
            except (ValueError, TypeError):
                score = 0
                self._separation_progress.setValue(score)
                self._separation_progress.setToolTip("분리도 데이터 오류")
        else:
            score = 0
            self._separation_progress.setValue(score)
            self._separation_progress.setToolTip("NG 이미지 없음 — 분리도 계산 불가")
        
        # Update AI summary with defensive access
        ai_summary = getattr(result, 'ai_summary', None)
        self._ai_summary_text.setText(ai_summary or "AI 분석을 사용할 수 없습니다.")
        
        # Update recommendations list with defensive access
        self._recommendations_list.clear()
        recommendations = getattr(result, 'preprocessing_recommendations', [])
        for recommendation in recommendations:
            item = QListWidgetItem(recommendation)
            self._recommendations_list.addItem(item)


class ResultPage(BasePage):
    """
    Results page for displaying analysis outcomes.
    
    Shows detailed analysis results including algorithm parameters,
    performance metrics, and visual overlays.
    """
    
    def __init__(self, parent=None):
        """Initialize the result page."""
        super().__init__(PageID.RESULTS, "결과 보기", parent)
        self._pending_result = None
        
    def setup_ui(self) -> None:
        """Setup the result page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("결과 보기", "분석 결과, 파라미터 및 성능 지표")
        layout.addWidget(header)
        
        
        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2A2A4A;
                background-color: #1A1A2E;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #16213E;
                color: #9E9E9E;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #1E88E5;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background-color: #424242;
                color: #E0E0E0;
            }
        """)
        
        # Create tabs
        self._create_tabs()
        
        layout.addWidget(self._tab_widget)
        
    def _create_tabs(self) -> None:
        """Create all result tabs."""
        # 1. 요약 tab
        self._summary_tab = SummaryTab()
        self._tab_widget.addTab(self._summary_tab, "요약")

        # 2. Feature 분석 tab (fully implemented)
        self._feature_tab = FeatureTab()
        self._tab_widget.addTab(self._feature_tab, "Feature 분석")

        # 3. Align 결과 tab (fully implemented)
        self._align_tab = AlignTab()
        self._tab_widget.addTab(self._align_tab, "Align 결과")

        # 4. Inspection 결과 tab (skeleton)
        self._inspection_tab = InspectionTab()
        self._tab_widget.addTab(self._inspection_tab, "Inspection 결과")

        # 5. Feasibility tab (skeleton)
        self._feasibility_tab = FeasibilityTab()
        self._tab_widget.addTab(self._feasibility_tab, "Feasibility")
        
    def load_result(self, result: FullFeatureAnalysis) -> None:
        """
        Load analysis result and switch to feature analysis tab.
        
        Args:
            result: The FullFeatureAnalysis result to display
        """
        self._pending_result = result
        self._apply_result()
        
    def _apply_result(self) -> None:
        """Apply the pending result data to UI components."""
        result = self._pending_result
        if result is None:
            return
            
        # Load data into feature tab
        self._feature_tab.load_data(result)
        
        # Switch to feature analysis tab
        self._tab_widget.setCurrentIndex(1)  # Index 1 is the "이미지 특성" tab

    def load_feature_result(self, result) -> None:
        """
        Load feature analysis result into the Feature 분석 tab.

        Args:
            result: FullFeatureAnalysis instance (or None).
        """
        if result is None:
            return
        self._pending_result = result
        self._apply_result()

    def load_align_result(self, result) -> None:
        """
        Load AlignResult and switch to the Align 결과 tab.

        Args:
            result: AlignResult or FallbackAlignResult instance (or None).
        """
        if result is None:
            return
        self._align_tab.load_result(result)

    def load_summary(self, aggregate) -> None:
        """
        Fill the Summary tab from the aggregate dict.

        Args:
            aggregate: dict with feature/align/inspection/evaluation/inspection_purpose.
        """
        if aggregate is None:
            return
        self._summary_tab.load_data(aggregate)

    def load_inspection_result(self, result) -> None:
        """
        Fill the Inspection 결과 tab skeleton.

        Args:
            result: OptimizationResult or None.
        """
        self._inspection_tab.load_data(result)

    def load_feasibility_result(self, result) -> None:
        """
        Fill the Feasibility tab skeleton.

        Args:
            result: FeasibilityResult or None.
        """
        self._feasibility_tab.load_data(result)

    def load_all(self, aggregate) -> None:
        """
        Convenience dispatcher — fills every tab from the aggregate dict.

        Args:
            aggregate: dict with keys: feature, align, inspection,
                       evaluation (dict with failure_result/feasibility_result),
                       inspection_purpose.
        """
        if aggregate is None:
            return

        # Summary
        self.load_summary(aggregate)

        # Feature
        self.load_feature_result(aggregate.get("feature"))

        # Align
        self.load_align_result(aggregate.get("align"))

        # Inspection
        self.load_inspection_result(aggregate.get("inspection"))

        # Feasibility
        eval_dict = aggregate.get("evaluation")
        feas = (
            eval_dict.get("feasibility_result")
            if isinstance(eval_dict, dict)
            else None
        )
        self.load_feasibility_result(feas)

        # Switch to summary tab
        self._tab_widget.setCurrentIndex(0)

