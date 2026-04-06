"""
Image upload page for the Argos vision algorithm design application.

This module provides the image upload interface for managing
training and test images.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID


class UploadPage(BasePage):
    """
    Image upload page for managing project images.
    
    Allows users to upload and organize images for align reference,
    inspection OK samples, and inspection NG samples.
    """
    
    def __init__(self, parent=None):
        """Initialize the upload page."""
        super().__init__(PageID.UPLOAD, "이미지 업로드", parent)
        
    def setup_ui(self) -> None:
        """Setup the upload page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("이미지 업로드", "Align, OK, NG 샘플 이미지 관리")
        layout.addWidget(header)
        
        # Placeholder content
        placeholder_label = QLabel("이미지 업로드 — 준비 중")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 16px;
                padding: 40px;
            }
        """)
        layout.addWidget(placeholder_label)