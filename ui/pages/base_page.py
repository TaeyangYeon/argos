"""
Base page components for the Argos vision algorithm design application.

This module provides abstract base classes for creating consistent page
layouts with headers and standardized structure.
"""

from abc import abstractmethod
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.components.sidebar import PageID


class PageHeader(QWidget):
    """
    Standard page header component with title and subtitle.
    
    Provides consistent header styling across all application pages.
    """
    
    def __init__(self, title: str, subtitle: str = "", parent=None):
        """
        Initialize the page header.
        
        Args:
            title: Main title text
            subtitle: Optional subtitle text
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._setup_ui(title, subtitle)
        
    def _setup_ui(self, title: str, subtitle: str) -> None:
        """Setup the header UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(4)
        
        # Title label
        self._title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(self._title_label)
        
        # Subtitle label (if provided)
        if subtitle:
            self._subtitle_label = QLabel(subtitle)
            subtitle_font = QFont()
            subtitle_font.setPointSize(13)
            self._subtitle_label.setFont(subtitle_font)
            self._subtitle_label.setStyleSheet("color: #9E9E9E;")
            layout.addWidget(self._subtitle_label)
        else:
            self._subtitle_label = None
            
        # Horizontal divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: #2A2A4A;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
    def update_title(self, title: str) -> None:
        """
        Update the header title.
        
        Args:
            title: New title text
        """
        self._title_label.setText(title)
        
    def update_subtitle(self, subtitle: str) -> None:
        """
        Update the header subtitle.
        
        Args:
            subtitle: New subtitle text
        """
        if self._subtitle_label is not None:
            self._subtitle_label.setText(subtitle)
        elif subtitle:
            # Create subtitle label if it doesn't exist
            subtitle_font = QFont()
            subtitle_font.setPointSize(13)
            
            self._subtitle_label = QLabel(subtitle)
            self._subtitle_label.setFont(subtitle_font)
            self._subtitle_label.setStyleSheet("color: #9E9E9E;")
            
            # Insert after title, before divider
            layout = self.layout()
            layout.insertWidget(1, self._subtitle_label)


class BasePage(QWidget):
    """
    Abstract base class for all application pages.
    
    Provides common structure and properties that all pages should have,
    including page identification and standardized layout.
    """
    
    def __init__(self, page_id: PageID, title: str, parent=None):
        """
        Initialize the base page.
        
        Args:
            page_id: Unique identifier for this page
            title: Display title for the page
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._page_id = page_id
        self._title = title
        
        # Setup UI after properties are set
        self.setup_ui()
        
    @property
    def page_id(self) -> PageID:
        """Get the page identifier."""
        return self._page_id
        
    @property
    def title(self) -> str:
        """Get the page title."""
        return self._title
        
    @abstractmethod
    def setup_ui(self) -> None:
        """
        Setup the page UI components.
        
        This method must be implemented by all subclasses to define
        the specific layout and widgets for each page.
        """
        pass