"""
Stat card component for the Argos vision algorithm design application.

This module provides a reusable stat card widget for displaying metrics
with title, value, and subtitle in a styled card format.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class StatCard(QFrame):
    """
    A styled card widget for displaying statistical information.
    
    Features:
    - Title, value, and subtitle display
    - Configurable accent color for left border and value text
    - Fixed height and minimum width for consistent layout
    - Dark theme compatible styling
    """
    
    def __init__(
        self, 
        title: str, 
        value: str, 
        subtitle: str = "", 
        accent_color: str = "#1E88E5", 
        parent=None
    ):
        """
        Initialize the stat card.
        
        Args:
            title: Main title text (12px, muted color)
            value: Large value text (28px, bold, accent color)
            subtitle: Optional subtitle text (11px, muted color)
            accent_color: Color for left border and value text
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._accent_color = accent_color
        
        self._setup_ui()
        self._apply_styling()
        
    def _setup_ui(self) -> None:
        """Setup the card UI layout."""
        # Set object name for styling
        self.setObjectName("card")
        
        # Fixed dimensions
        self.setFixedHeight(100)
        self.setMinimumWidth(160)
        
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title label
        self._title_label = QLabel(self._title)
        title_font = QFont()
        title_font.setPointSize(12)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(self._title_label)
        
        # Value label
        self._value_label = QLabel(self._value)
        value_font = QFont()
        value_font.setPointSize(28)
        value_font.setBold(True)
        self._value_label.setFont(value_font)
        self._value_label.setStyleSheet(f"color: {self._accent_color};")
        layout.addWidget(self._value_label)
        
        # Subtitle label (if provided)
        if self._subtitle:
            self._subtitle_label = QLabel(self._subtitle)
            subtitle_font = QFont()
            subtitle_font.setPointSize(11)
            self._subtitle_label.setFont(subtitle_font)
            self._subtitle_label.setStyleSheet("color: #616161;")
            layout.addWidget(self._subtitle_label)
        else:
            self._subtitle_label = None
            
    def _apply_styling(self) -> None:
        """Apply the card styling with accent color border."""
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-left: 4px solid {self._accent_color};
                border-radius: 8px;
            }}
            QFrame#card:hover {{
                background-color: #1E2A4A;
            }}
        """)
        
    def update_value(self, value: str, subtitle: str = "") -> None:
        """
        Update the value and subtitle labels dynamically.
        
        Args:
            value: New value text
            subtitle: New subtitle text (optional)
        """
        self._value = value
        self._subtitle = subtitle
        
        # Update value label
        self._value_label.setText(value)
        
        # Update or create subtitle label
        if subtitle:
            if self._subtitle_label is None:
                # Create subtitle label if it doesn't exist
                subtitle_font = QFont()
                subtitle_font.setPointSize(11)
                
                self._subtitle_label = QLabel(subtitle)
                self._subtitle_label.setFont(subtitle_font)
                self._subtitle_label.setStyleSheet("color: #616161;")
                
                # Add to layout
                self.layout().addWidget(self._subtitle_label)
            else:
                # Update existing subtitle
                self._subtitle_label.setText(subtitle)
                self._subtitle_label.setVisible(True)
        else:
            # Hide subtitle if empty
            if self._subtitle_label is not None:
                self._subtitle_label.setVisible(False)
                
    def set_accent(self, color: str) -> None:
        """
        Update the accent color for border and value text.
        
        Args:
            color: New accent color (hex format, e.g., "#43A047")
        """
        self._accent_color = color
        
        # Update value text color
        self._value_label.setStyleSheet(f"color: {color};")
        
        # Update border styling
        self._apply_styling()