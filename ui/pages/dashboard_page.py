"""
Dashboard page for the Argos vision algorithm design application.

This module provides the main dashboard page with project overview
and status information.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
    QScrollArea, QWidget, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID
from ui.components.stat_card import StatCard
from ui.components.workflow_indicator import WorkflowIndicator
from core.image_store import ImageStore, ImageType
from core.key_manager import KeyManager
from core.providers.base_provider import ProviderStatus


class DashboardPage(BasePage):
    """
    Dashboard page displaying project overview and current status.
    
    Features:
    - StatCards showing image counts by type
    - AI connection status display
    - Workflow progress indicator
    - Recent analysis results summary
    - New project reset functionality
    """
    
    # Signal emitted when session is reset
    session_reset = pyqtSignal()
    
    # Signal emitted when navigation is requested
    navigate_requested = pyqtSignal(str)
    
    def __init__(self, image_store: ImageStore, key_manager: KeyManager, parent=None):
        """
        Initialize the dashboard page.
        
        Args:
            image_store: ImageStore instance for data access
            key_manager: KeyManager instance for AI connection status
            parent: Parent widget
        """
        self._image_store = image_store
        self._key_manager = key_manager
        
        # Initialize stat cards as None - they'll be created in setup_ui
        self._align_ok_card = None
        self._inspection_ok_card = None
        self._inspection_ng_card = None
        self._total_card = None
        self._purpose_card = None

        # Initialize workflow indicator
        self._workflow_indicator = None

        # Track workflow state
        self._has_roi = False
        self._has_purpose = False
        self._has_results = False
        self._purpose_type = ""
        
        super().__init__(PageID.DASHBOARD, "대시보드", parent)
        
    def setup_ui(self) -> None:
        """Setup the dashboard page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("대시보드", "현재 세션 현황")
        layout.addWidget(header)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(16)
        
        # Stat cards row
        self._setup_stat_cards(content_layout)
        
        # AI connection status card
        self._setup_ai_status_card(content_layout)
        
        # Workflow indicator
        self._setup_workflow_indicator(content_layout)
        
        # Recent analysis results card
        self._setup_recent_results_card(content_layout)
        
        # New project button
        self._setup_new_project_button(content_layout)
        
        # Add stretch to push content to top
        content_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Set content widget to scroll area and add to main layout
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
    def _setup_stat_cards(self, parent_layout: QVBoxLayout) -> None:
        """Setup the stat cards row."""
        # Cards container
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        # Create stat cards with specified colors
        self._align_ok_card = StatCard("Align OK", "0", "", "#1E88E5")  # blue
        self._inspection_ok_card = StatCard("Inspection OK", "0", "", "#43A047")  # green
        self._inspection_ng_card = StatCard("Inspection NG", "0", "", "#E53935")  # red
        self._total_card = StatCard("전체", "0", "", "#FB8C00")  # amber
        self._purpose_card = StatCard("검사 목적", "미입력", "", "#9E9E9E")  # gray default

        # Add cards to layout with equal stretch
        cards_layout.addWidget(self._align_ok_card, 1)
        cards_layout.addWidget(self._inspection_ok_card, 1)
        cards_layout.addWidget(self._inspection_ng_card, 1)
        cards_layout.addWidget(self._total_card, 1)
        cards_layout.addWidget(self._purpose_card, 1)
        
        parent_layout.addLayout(cards_layout)
        
    def _setup_ai_status_card(self, parent_layout: QVBoxLayout) -> None:
        """Setup the AI connection status card."""
        self._ai_status_card = QFrame()
        self._ai_status_card.setObjectName("card")
        self._ai_status_card.setFixedHeight(80)
        
        card_layout = QHBoxLayout(self._ai_status_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(12)
        
        # AI status icon and text
        self._ai_status_label = QLabel()
        status_font = QFont()
        status_font.setPointSize(14)
        status_font.setBold(True)
        self._ai_status_label.setFont(status_font)
        card_layout.addWidget(self._ai_status_label)
        
        # Spacer
        card_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        parent_layout.addWidget(self._ai_status_card)
        
    def _setup_workflow_indicator(self, parent_layout: QVBoxLayout) -> None:
        """Setup the workflow progress indicator."""
        workflow_card = QFrame()
        workflow_card.setObjectName("card")
        
        card_layout = QVBoxLayout(workflow_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # Create workflow indicator
        self._workflow_indicator = WorkflowIndicator()
        card_layout.addWidget(self._workflow_indicator)
        
        parent_layout.addWidget(workflow_card)
        
    def _setup_recent_results_card(self, parent_layout: QVBoxLayout) -> None:
        """Setup the recent analysis results card."""
        results_card = QFrame()
        results_card.setObjectName("card")
        results_card.setFixedHeight(120)
        
        card_layout = QVBoxLayout(results_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(8)
        
        # Title
        title_label = QLabel("최근 분석 결과")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E0E0E0;")
        card_layout.addWidget(title_label)
        
        # Content
        self._results_content_label = QLabel("아직 분석 결과가 없습니다.\n이미지를 업로드하고 분석을 시작하세요.")
        self._results_content_label.setStyleSheet("color: #9E9E9E; font-size: 12px;")
        self._results_content_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        card_layout.addWidget(self._results_content_label)
        
        parent_layout.addWidget(results_card)
        
    def _setup_new_project_button(self, parent_layout: QVBoxLayout) -> None:
        """Setup the new project reset button."""
        button_layout = QHBoxLayout()
        
        # Spacer to center the button
        button_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # New project button
        self._new_project_button = QPushButton("🔄 새 프로젝트 시작")
        self._new_project_button.setObjectName("dangerBtn")
        self._new_project_button.clicked.connect(self._on_new_project_clicked)
        button_layout.addWidget(self._new_project_button)
        
        # Spacer
        button_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        parent_layout.addLayout(button_layout)
        
    def _on_new_project_clicked(self) -> None:
        """Handle new project button click with confirmation."""
        # Show confirmation dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("새 프로젝트 시작")
        msg_box.setText("현재 세션의 모든 데이터가 초기화됩니다. 계속하시겠습니까?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            # User confirmed - clear session data
            self._image_store.clear()

            # Reset tracked workflow state
            self._has_roi = False
            self._has_purpose = False
            self._has_results = False
            self._purpose_type = ""

            # Reset workflow indicator
            if self._workflow_indicator:
                self._workflow_indicator.reset()

            # Refresh dashboard
            self.refresh()

            # Emit session reset signal
            self.session_reset.emit()
            
    def on_purpose_confirmed(self, purpose) -> None:
        """Handle inspection purpose confirmation from PurposePage."""
        self._has_purpose = True
        self._purpose_type = getattr(purpose, "inspection_type", "")
        self._update_purpose_card()
        self._refresh_workflow()

    def on_roi_confirmed(self, roi_config) -> None:
        """Handle ROI confirmation from ROIPage."""
        self._has_roi = True
        self._refresh_workflow()

    def on_analysis_complete(self, aggregate) -> None:
        """Handle analysis completion from AnalysisWorker via MainWindow."""
        self._has_results = True
        self._refresh_workflow()

        # Update recent results card
        if self._results_content_label:
            self._results_content_label.setText("분석 완료 — 결과 보기 탭에서 상세 내용을 확인하세요.")
            self._results_content_label.setStyleSheet("color: #43A047; font-size: 12px;")

    def _update_purpose_card(self) -> None:
        """Update the purpose StatCard based on current state."""
        if self._purpose_card:
            if self._has_purpose:
                display = self._purpose_type if self._purpose_type else "확정됨"
                self._purpose_card.update_value("확정됨", display)
                self._purpose_card.set_accent("#43A047")  # green
            else:
                self._purpose_card.update_value("미입력")
                self._purpose_card.set_accent("#9E9E9E")  # gray

    def _refresh_workflow(self) -> None:
        """Update workflow indicator with current tracked state."""
        if self._workflow_indicator:
            self._workflow_indicator.update_from_store(
                self._image_store,
                self._has_roi,
                self._has_results,
                self._has_purpose,
            )

    def refresh(self) -> None:
        """
        Update all dashboard components with current data.

        Called every time the dashboard becomes visible.
        """
        # Update stat cards
        if self._align_ok_card:
            align_ok_count = self._image_store.count(ImageType.ALIGN_OK)
            self._align_ok_card.update_value(str(align_ok_count))

        if self._inspection_ok_card:
            inspection_ok_count = self._image_store.count(ImageType.INSPECTION_OK)
            self._inspection_ok_card.update_value(str(inspection_ok_count))

        if self._inspection_ng_card:
            inspection_ng_count = self._image_store.count(ImageType.INSPECTION_NG)
            self._inspection_ng_card.update_value(str(inspection_ng_count))

        if self._total_card:
            total_count = self._image_store.count()
            self._total_card.update_value(str(total_count))

        # Update purpose card
        self._update_purpose_card()

        # Update AI status
        self._update_ai_status()

        # Update workflow indicator
        self._refresh_workflow()
            
    def _update_ai_status(self) -> None:
        """Update the AI connection status display."""
        # Check if any provider has a saved key
        saved_providers = self._key_manager.list_saved_providers()
        
        if saved_providers:
            # Show connected status for the first saved provider
            provider_name = saved_providers[0].title()
            self._ai_status_label.setText(f"● {provider_name} 연결됨")
            self._ai_status_label.setStyleSheet("color: #43A047;")  # green
        else:
            # No saved providers
            self._ai_status_label.setText("AI 미연결 — API 입력 버튼을 눌러 연결하세요.")
            self._ai_status_label.setStyleSheet("color: #9E9E9E;")  # muted
            
    def showEvent(self, event) -> None:
        """Override showEvent to refresh data when dashboard becomes visible."""
        super().showEvent(event)
        self.refresh()