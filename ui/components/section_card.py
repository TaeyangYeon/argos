"""
Section card component for the Argos vision algorithm design application.

This module provides a reusable card widget with title and content area
for organizing related settings or controls in a visually consistent manner.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SectionCard(QFrame):
    """
    Card-style container widget for grouping related settings.
    
    Features:
    - Styled header with section title
    - Horizontal divider line
    - Content area for adding widgets
    - Helper methods for adding labeled rows
    """
    
    def __init__(self, title: str, parent=None):
        """
        Initialize the section card.
        
        Args:
            title: Section title displayed at the top
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        self._setup_ui(title)
        
    def _setup_ui(self, title: str) -> None:
        """Setup the card UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Section title
        title_label = QLabel(title.upper())
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(title_label)
        
        # Horizontal divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #2A2A4A; border: none; background-color: #2A2A4A;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        # Content area
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 8, 0, 0)
        self._content_layout.setSpacing(12)
        layout.addLayout(self._content_layout)
        
    def add_widget(self, widget: QWidget) -> None:
        """
        Add a widget to the content area.
        
        Args:
            widget: Widget to add
        """
        self._content_layout.addWidget(widget)
        
    def add_row(self, label: str, widget: QWidget) -> None:
        """
        Add a horizontal row with label and widget.
        
        Args:
            label: Label text (displayed on left, 140px fixed width)
            widget: Widget to display on right (expanding)
        """
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)
        
        # Label (fixed width)
        label_widget = QLabel(label)
        label_font = QFont()
        label_font.setPointSize(12)
        label_widget.setFont(label_font)
        label_widget.setStyleSheet("color: #E0E0E0;")
        label_widget.setFixedWidth(140)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row_layout.addWidget(label_widget)
        
        # Widget (expanding)
        row_layout.addWidget(widget, 1)
        
        # Add row to content layout
        self._content_layout.addLayout(row_layout)