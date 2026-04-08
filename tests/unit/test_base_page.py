"""
Tests for base page components.

This module tests the BasePage and PageHeader classes,
and validates the concrete page implementations.
"""

import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QLabel

from ui.pages.base_page import BasePage, PageHeader
from ui.pages.dashboard_page import DashboardPage
from ui.pages.upload_page import UploadPage
from ui.components.sidebar import PageID


class TestPageHeader:
    """Test cases for PageHeader class."""
    
    @pytest.fixture
    def page_header(self, qtbot):
        """Create a PageHeader instance for testing."""
        header = PageHeader("Test Title", "Test Subtitle")
        qtbot.addWidget(header)
        return header
    
    def test_page_header_shows_title(self, page_header):
        """Test that page header displays the title correctly."""
        title_label = page_header._title_label
        assert isinstance(title_label, QLabel)
        assert title_label.text() == "Test Title"
        
    def test_page_header_shows_subtitle(self, page_header):
        """Test that page header displays the subtitle correctly."""
        subtitle_label = page_header._subtitle_label
        assert isinstance(subtitle_label, QLabel)
        assert subtitle_label.text() == "Test Subtitle"
        
    def test_page_header_update_title(self, page_header):
        """Test updating the page header title."""
        page_header.update_title("New Title")
        assert page_header._title_label.text() == "New Title"
        
    def test_page_header_update_subtitle(self, page_header):
        """Test updating the page header subtitle."""
        page_header.update_subtitle("New Subtitle")
        assert page_header._subtitle_label.text() == "New Subtitle"


class TestConcretePages:
    """Test cases for concrete page implementations."""
    
    @pytest.fixture
    def dashboard_page(self, qtbot):
        """Create a DashboardPage instance for testing."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        return page
        
    @pytest.fixture
    def upload_page(self, qtbot):
        """Create an UploadPage instance for testing."""
        mock_image_store = MagicMock()
        # Mock the count method to return 0 for all image types
        mock_image_store.count.return_value = 0
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        return page
    
    def test_dashboard_page_has_correct_page_id(self, dashboard_page):
        """Test that DashboardPage has correct page ID."""
        assert dashboard_page.page_id == PageID.DASHBOARD
        
    def test_upload_page_has_correct_title(self, upload_page):
        """Test that UploadPage has correct title."""
        assert upload_page.title == "이미지 업로드"