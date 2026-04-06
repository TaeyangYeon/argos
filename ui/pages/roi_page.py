"""
ROI (Region of Interest) configuration page for the Argos vision algorithm design application.

This module provides the interface for defining and adjusting
regions of interest for vision analysis.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID


class ROIPage(BasePage):
    """
    ROI configuration page for defining analysis regions.
    
    Allows users to define regions of interest on images
    using mouse interaction and coordinate input.
    """
    
    def __init__(self, parent=None):
        """Initialize the ROI page."""
        super().__init__(PageID.ROI, "ROI 설정", parent)
        
    def setup_ui(self) -> None:
        """Setup the ROI page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("ROI 설정", "검사 영역 정의 및 좌표 설정")
        layout.addWidget(header)
        
        # Placeholder content
        placeholder_label = QLabel("ROI 설정 — 준비 중")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 16px;
                padding: 40px;
            }
        """)
        layout.addWidget(placeholder_label)