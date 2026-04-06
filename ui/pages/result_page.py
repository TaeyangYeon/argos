"""
Results viewing page for the Argos vision algorithm design application.

This module provides the interface for viewing analysis results,
algorithm parameters, and performance metrics.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID


class ResultPage(BasePage):
    """
    Results page for displaying analysis outcomes.
    
    Shows detailed analysis results including algorithm parameters,
    performance metrics, and visual overlays.
    """
    
    def __init__(self, parent=None):
        """Initialize the result page."""
        super().__init__(PageID.RESULTS, "결과 보기", parent)
        
    def setup_ui(self) -> None:
        """Setup the result page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("결과 보기", "분석 결과, 파라미터 및 성능 지표")
        layout.addWidget(header)
        
        # Placeholder content
        placeholder_label = QLabel("결과 보기 — 준비 중")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 16px;
                padding: 40px;
            }
        """)
        layout.addWidget(placeholder_label)