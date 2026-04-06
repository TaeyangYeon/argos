"""
Main window for the Argos vision algorithm design application.

This module provides the MainWindow class which sets up the primary application
window with dark theme, sidebar layout, and status bar.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QFrame, 
    QStackedWidget, QStatusBar, QLabel
)
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QIcon

from core.logger import get_logger
from ui.style import DARK_THEME_QSS


class MainWindow(QMainWindow):
    """
    Main application window for Argos.
    
    Provides the primary layout with sidebar navigation, content area,
    and status bar with connection status display.
    """
    
    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        
        self._logger = get_logger("main_window")
        self._setup_window()
        self._setup_layout()
        self._setup_status_bar()
        
    def _setup_window(self) -> None:
        """Setup window properties."""
        self.setWindowTitle("Argos — Vision Algorithm Agent")
        self.setMinimumSize(1280, 800)
        
        # Apply dark theme
        self.setStyleSheet(DARK_THEME_QSS)
        
        # Set window icon if it exists
        icon_path = Path(__file__).parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            
        self._logger.info("Main window initialized")
    
    def _setup_layout(self) -> None:
        """Setup the main window layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout (no margins)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left sidebar (fixed width 220px)
        self._sidebar_frame = QFrame()
        self._sidebar_frame.setObjectName("sidebar")
        self._sidebar_frame.setFixedWidth(220)
        self._sidebar_frame.setMaximumWidth(220)
        
        # Right content area (expandable)
        self._content_area = QStackedWidget()
        self._content_area.setObjectName("content")
        
        # Add to layout
        main_layout.addWidget(self._sidebar_frame)
        main_layout.addWidget(self._content_area)
        
    def _setup_status_bar(self) -> None:
        """Setup the status bar with version and connection status."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Left label: Version
        version_label = QLabel("Argos v0.1.0")
        status_bar.addWidget(version_label)
        
        # Right label: Connection status
        self._connection_label = QLabel()
        self.set_connection_status(False)  # Initially disconnected
        status_bar.addPermanentWidget(self._connection_label)
        
    def closeEvent(self, event: QEvent) -> None:
        """Handle window close event."""
        self._on_close(event)
        
    def _on_close(self, event: QEvent) -> None:
        """Log application closing and accept the event."""
        self._logger.info("Application closing")
        event.accept()
        
    def set_connection_status(self, connected: bool, provider_name: str = "") -> None:
        """
        Update the connection status in the status bar.
        
        Args:
            connected: Whether AI provider is connected
            provider_name: Name of the connected AI provider
        """
        if connected and provider_name:
            status_text = f'<span style="color: #43A047;">● 연결됨 ({provider_name})</span>'
        else:
            status_text = '<span style="color: #E53935;">● 미연결</span>'
            
        self._connection_label.setText(status_text)
        self._logger.debug(f"Connection status updated: connected={connected}, provider={provider_name}")
        
    def get_content_area(self) -> QStackedWidget:
        """
        Get the content area widget for adding pages.
        
        Returns:
            The main content QStackedWidget
        """
        return self._content_area
        
    def get_sidebar_frame(self) -> QFrame:
        """
        Get the sidebar frame for adding navigation widgets.
        
        Returns:
            The sidebar QFrame widget
        """
        return self._sidebar_frame