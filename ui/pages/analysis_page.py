"""
Analysis execution page for the Argos vision algorithm design application.

This module provides the interface for running vision algorithm
analysis and monitoring progress.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID


class AnalysisPage(BasePage):
    """
    Analysis execution page for running vision algorithms.
    
    Provides controls for starting analysis, monitoring progress,
    and viewing real-time logs during algorithm execution.
    """
    
    def __init__(self, parent=None):
        """Initialize the analysis page."""
        super().__init__(PageID.ANALYSIS, "분석 실행", parent)
        
    def setup_ui(self) -> None:
        """Setup the analysis page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("분석 실행", "알고리즘 분석 시작 및 진행 상태 모니터링")
        layout.addWidget(header)
        
        # Placeholder content
        placeholder_label = QLabel("분석 실행 — 준비 중")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 16px;
                padding: 40px;
            }
        """)
        layout.addWidget(placeholder_label)