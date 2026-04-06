"""
Tests for the main toolbar implementation.

This module tests the ArgosToolbar class functionality including widget creation,
API button functionality, and connection status display.
"""

import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QPushButton

from ui.components.toolbar import ArgosToolbar
from ui.components.status_indicator import ConnectionStatusWidget
from core.key_manager import KeyManager
from core.providers.provider_factory import ProviderFactory


class TestArgosToolbar:
    """Test cases for ArgosToolbar class."""
    
    @pytest.fixture
    def mock_key_manager(self):
        """Create a mock KeyManager instance."""
        mock = MagicMock(spec=KeyManager)
        mock.exists.return_value = False
        return mock
    
    @pytest.fixture
    def mock_provider_factory(self):
        """Create a mock ProviderFactory instance."""
        mock = MagicMock(spec=ProviderFactory)
        return mock
    
    @pytest.fixture
    def toolbar(self, qtbot, mock_key_manager, mock_provider_factory):
        """Create an ArgosToolbar instance for testing."""
        toolbar = ArgosToolbar(mock_key_manager, mock_provider_factory)
        qtbot.addWidget(toolbar)
        return toolbar
    
    def test_toolbar_created(self, toolbar):
        """Test that toolbar is created without error."""
        assert toolbar is not None
        assert toolbar.objectName() == "mainToolbar"
        assert toolbar.isMovable() is False
        assert toolbar.isFloatable() is False
    
    def test_api_button_exists(self, toolbar):
        """Test that toolbar contains API input button."""
        # Find the API button by searching through toolbar widgets
        api_button = None
        for action in toolbar.actions():
            widget = toolbar.widgetForAction(action)
            if isinstance(widget, QPushButton) and "API 입력" in widget.text():
                api_button = widget
                break
        
        # Also check direct children
        if api_button is None:
            for child in toolbar.findChildren(QPushButton):
                if "API 입력" in child.text():
                    api_button = child
                    break
        
        assert api_button is not None
        assert "API 입력" in api_button.text()
        assert api_button.objectName() == "primaryBtn"
    
    def test_connection_status_widget_exists(self, toolbar):
        """Test that toolbar contains ConnectionStatusWidget."""
        # Find the ConnectionStatusWidget
        status_widget = None
        for child in toolbar.findChildren(ConnectionStatusWidget):
            status_widget = child
            break
        
        assert status_widget is not None
        assert isinstance(status_widget, ConnectionStatusWidget)