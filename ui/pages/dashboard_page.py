"""
Dashboard page for the Argos vision algorithm design application.

This module provides the main dashboard page with project overview
and status information.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID


class DashboardPage(BasePage):
    """
    Dashboard page displaying project overview and current status.
    
    This is the main landing page that shows project status,
    recent activity, and quick access to common functions.
    """
    
    def __init__(self, parent=None):
        """Initialize the dashboard page."""
        super().__init__(PageID.DASHBOARD, "대시보드", parent)
        
    def setup_ui(self) -> None:
        """Setup the dashboard page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("대시보드", "프로젝트 현황 및 상태 정보")
        layout.addWidget(header)
        
        # Placeholder content
        placeholder_label = QLabel("대시보드 — 준비 중")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 16px;
                padding: 40px;
            }
        """)
        layout.addWidget(placeholder_label)