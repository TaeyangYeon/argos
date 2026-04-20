"""
Tests for the main window implementation.

This module tests the MainWindow class functionality including window setup,
layout, and connection status management.
"""

import pytest
from PyQt6.QtWidgets import QFrame, QStackedWidget
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


class TestMainWindow:
    """Test cases for MainWindow class."""
    
    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window
    
    def test_main_window_title(self, main_window):
        """Test that window title is correctly set."""
        from core import __version__
        assert main_window.windowTitle() == f"Argos v{__version__} — Vision Algorithm Agent"
    
    def test_main_window_minimum_size(self, main_window):
        """Test that minimum window size is correctly set."""
        min_size = main_window.minimumSize()
        assert min_size.width() >= 1280
        assert min_size.height() >= 800
    
    def test_sidebar_frame_exists(self, main_window):
        """Test that sidebar frame is created and accessible."""
        sidebar = main_window.get_sidebar()
        assert sidebar is not None
        assert sidebar.objectName() == "sidebar"
    
    def test_content_area_exists(self, main_window):
        """Test that content area is created and accessible."""
        content_area = main_window.get_content_area()
        assert isinstance(content_area, QStackedWidget)
        assert content_area.objectName() == "content"
    
    def test_sidebar_fixed_width(self, main_window):
        """Test that sidebar has fixed width of 220px."""
        sidebar = main_window.get_sidebar()
        assert sidebar.maximumWidth() == 220
        assert sidebar.width() <= 220
    
    def test_set_connection_status_connected(self, main_window):
        """Test connection status when connected."""
        # Connection status is now handled by toolbar, just test method exists and doesn't crash
        main_window.set_connection_status(True, "Claude")
        # Method should complete without error (logs internally)
    
    def test_set_connection_status_disconnected(self, main_window):
        """Test connection status when disconnected."""
        # Connection status is now handled by toolbar, just test method exists and doesn't crash  
        main_window.set_connection_status(False)
        # Method should complete without error (logs internally)
    
    def test_dark_theme_applied(self, main_window):
        """Test that dark theme stylesheet is applied."""
        stylesheet = main_window.styleSheet()
        assert stylesheet is not None
        assert len(stylesheet) > 0
        # Check for key dark theme colors
        assert "#1A1A2E" in stylesheet  # Main background color
        assert "#16213E" in stylesheet  # Card background color