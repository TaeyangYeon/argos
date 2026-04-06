"""
Settings page for the Argos vision algorithm design application.

This module provides the interface for configuring application
settings and algorithm parameters.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID


class SettingsPage(BasePage):
    """
    Settings page for application configuration.
    
    Provides controls for adjusting application settings,
    algorithm thresholds, and system preferences.
    """
    
    def __init__(self, parent=None):
        """Initialize the settings page."""
        super().__init__(PageID.SETTINGS, "설정", parent)
        
    def setup_ui(self) -> None:
        """Setup the settings page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("설정", "애플리케이션 설정 및 알고리즘 파라미터")
        layout.addWidget(header)
        
        # Placeholder content
        placeholder_label = QLabel("설정 — 준비 중")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 16px;
                padding: 40px;
            }
        """)
        layout.addWidget(placeholder_label)