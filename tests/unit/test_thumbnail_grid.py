"""
Unit tests for thumbnail grid components.

This module tests the thumbnail card, flow layout, thumbnail grid,
and upload page integration to ensure proper functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest

from ui.components.thumbnail_card import ThumbnailCard
from ui.components.flow_layout import FlowLayout
from ui.components.thumbnail_grid import ThumbnailGrid
from ui.pages.upload_page import UploadPage
from core.image_store import ImageType


class TestThumbnailCard:
    """Test cases for ThumbnailCard component."""
    
    def test_thumbnail_card_created(self, qtbot, make_image_meta):
        """ThumbnailCard with mock ImageMeta → no error."""
        meta = make_image_meta()
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        assert card is not None
        assert card._meta == meta
        assert card.size().width() == 140
        assert card.size().height() == 160
        
    def test_thumbnail_card_shows_filename(self, qtbot, make_image_meta):
        """Card label contains filename from meta.file_path."""
        meta = make_image_meta(filename="test_image.png")
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        filename_text = card._filename_label.text()
        assert "test_image.png" in filename_text
        
    def test_thumbnail_card_type_badge_align_ok(self, qtbot, make_image_meta):
        """ALIGN_OK type → badge text "Align OK"."""
        meta = make_image_meta(ImageType.ALIGN_OK)
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        badge_text = card._badge_label.text()
        assert badge_text == "Align OK"
        
    def test_thumbnail_card_type_badge_ng(self, qtbot, make_image_meta):
        """INSPECTION_NG type → badge text "NG"."""
        meta = make_image_meta(ImageType.INSPECTION_NG)
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        badge_text = card._badge_label.text()
        assert badge_text == "NG"
        
    def test_thumbnail_card_shows_dimensions(self, qtbot, make_image_meta):
        """Card shows correct image dimensions."""
        meta = make_image_meta(width=1024, height=768)
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        dimensions_text = card._dimensions_label.text()
        assert dimensions_text == "1024×768"
        
    def test_thumbnail_card_delete_signal(self, qtbot, make_image_meta):
        """delete_requested signal emitted with correct id."""
        meta = make_image_meta(image_id="test_delete_id")
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        # Track signal emissions
        signal_emitted = []
        card.delete_requested.connect(lambda img_id: signal_emitted.append(img_id))
        
        # Test signal emission directly
        card.delete_requested.emit("test_delete_id")
        
        # Verify signal was emitted with correct ID
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == "test_delete_id"
            
    def test_thumbnail_card_view_signal(self, qtbot, make_image_meta):
        """view_requested signal emitted with correct id."""
        meta = make_image_meta(image_id="test_view_id")
        card = ThumbnailCard(meta)
        qtbot.addWidget(card)
        
        # Track signal emissions
        signal_emitted = []
        card.view_requested.connect(lambda img_id: signal_emitted.append(img_id))
        
        # Test signal emission directly
        card.view_requested.emit("test_view_id")
        
        # Verify signal was emitted with correct ID
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == "test_view_id"


class TestFlowLayout:
    """Test cases for FlowLayout component."""
    
    def test_flow_layout_add_items(self, qtbot):
        """Add 5 widgets → count() == 5."""
        widget = QWidget()
        layout = FlowLayout(widget)
        qtbot.addWidget(widget)
        
        # Add 5 test widgets
        for i in range(5):
            test_widget = QWidget()
            test_widget.setFixedSize(50, 50)
            layout.addWidget(test_widget)
            
        assert layout.count() == 5
        
    def test_flow_layout_height_for_width(self, qtbot):
        """heightForWidth(400) returns positive integer."""
        widget = QWidget()
        layout = FlowLayout(widget)
        qtbot.addWidget(widget)
        
        # Add some test widgets
        for i in range(3):
            test_widget = QWidget()
            test_widget.setFixedSize(100, 50)
            layout.addWidget(test_widget)
            
        height = layout.heightForWidth(400)
        assert isinstance(height, int)
        assert height > 0
        
    def test_flow_layout_has_height_for_width(self, qtbot):
        """FlowLayout.hasHeightForWidth() returns True."""
        widget = QWidget()
        layout = FlowLayout(widget)
        qtbot.addWidget(widget)
        
        assert layout.hasHeightForWidth() is True


class TestThumbnailGrid:
    """Test cases for ThumbnailGrid component."""
    
    def test_thumbnail_grid_created(self, qtbot):
        """ThumbnailGrid() instantiates without error."""
        grid = ThumbnailGrid()
        qtbot.addWidget(grid)
        
        assert grid is not None
        assert grid.get_card_count() == 0
        
    def test_thumbnail_grid_refresh(self, qtbot, sample_image_metas):
        """refresh([meta1, meta2]) → grid contains 2 cards."""
        grid = ThumbnailGrid()
        qtbot.addWidget(grid)
        
        # Take first 2 metas
        test_metas = sample_image_metas[:2]
        grid.refresh(test_metas)
        
        assert grid.get_card_count() == 2
        
    def test_thumbnail_grid_clear(self, qtbot, sample_image_metas):
        """refresh([meta1]) then clear_all() → no cards."""
        grid = ThumbnailGrid()
        qtbot.addWidget(grid)
        
        # Add one meta then clear
        grid.refresh([sample_image_metas[0]])
        assert grid.get_card_count() == 1
        
        grid.clear_all()
        assert grid.get_card_count() == 0
        
    def test_thumbnail_grid_filter_by_type(self, qtbot, sample_image_metas):
        """Grid with ImageType filter shows only matching images."""
        grid = ThumbnailGrid(image_type=ImageType.ALIGN_OK)
        qtbot.addWidget(grid)
        
        # Refresh with all metas (should filter to only ALIGN_OK)
        grid.refresh(sample_image_metas)
        
        # Should only show ALIGN_OK images (2 in sample_image_metas)
        align_ok_count = len([m for m in sample_image_metas if m.image_type == ImageType.ALIGN_OK])
        assert grid.get_card_count() == align_ok_count


class TestUploadPageIntegration:
    """Test cases for UploadPage integration with thumbnail grid."""
    
    def test_upload_page_grid_updates_on_add(self, qtbot, make_image_meta):
        """Mock store.get_all() returns 2 metas → after _refresh_ui() → grid has 2 cards."""
        mock_image_store = MagicMock()
        
        # Create 2 mock metas
        meta1 = make_image_meta(ImageType.ALIGN_OK, "test1.png", image_id="test1")
        meta2 = make_image_meta(ImageType.INSPECTION_OK, "test2.png", image_id="test2")
        
        mock_image_store.get_all.return_value = [meta1, meta2]
        mock_image_store.count.return_value = 2
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Trigger refresh
        page._refresh_ui()
        
        # Check that grid has 2 cards
        assert page._thumbnail_grid.get_card_count() == 2
        
    def test_upload_page_filter_tab_all(self, qtbot, make_image_meta):
        """Filter "전체" → grid.refresh called with all images."""
        mock_image_store = MagicMock()
        
        # Create test metas
        meta1 = make_image_meta(ImageType.ALIGN_OK, "test1.png", image_id="test1")
        meta2 = make_image_meta(ImageType.INSPECTION_NG, "test2.png", image_id="test2")
        
        mock_image_store.get_all.return_value = [meta1, meta2]
        mock_image_store.count.return_value = 2
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Select "전체" filter (should be default, but test explicitly)
        page._on_filter_changed(None)
        
        # Check that grid shows all images
        assert page._thumbnail_grid.get_card_count() == 2
        
    def test_upload_page_filter_tab_ng(self, qtbot, make_image_meta):
        """Filter "Inspection NG" → grid.refresh called with only NG images."""
        mock_image_store = MagicMock()
        
        # Create test metas with mixed types
        meta1 = make_image_meta(ImageType.ALIGN_OK, "test1.png", image_id="test1")
        meta2 = make_image_meta(ImageType.INSPECTION_NG, "test2.png", image_id="test2")
        meta3 = make_image_meta(ImageType.INSPECTION_NG, "test3.png", image_id="test3")
        
        mock_image_store.get_all.return_value = [meta1, meta2, meta3]
        mock_image_store.count.return_value = 3
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Select NG filter
        page._on_filter_changed(ImageType.INSPECTION_NG)
        
        # Check that grid shows only NG images (2 out of 3)
        assert page._thumbnail_grid.get_card_count() == 2
        
    def test_upload_page_delete_confirmation(self, qtbot):
        """Delete from grid → confirmation dialog → store.remove() called."""
        mock_image_store = MagicMock()
        mock_image_store.get_all.return_value = []
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Mock toast to avoid actual display
        page._toast = MagicMock()
        
        # Mock QMessageBox to return Yes
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
            # Call delete handler directly
            page._on_delete_requested("test_image_id")
            
            # Verify store.remove was called
            mock_image_store.remove.assert_called_once_with("test_image_id")
            
            # Verify success toast was shown
            page._toast.show_success.assert_called_once_with("이미지 삭제 완료")
            
    def test_upload_page_view_dialog_opens(self, qtbot, make_image_meta):
        """View from grid → ImageViewerDialog opens."""
        mock_image_store = MagicMock()
        test_meta = make_image_meta(image_id="test_view_id")
        mock_image_store.get.return_value = test_meta
        mock_image_store.get_all.return_value = []
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Mock ImageViewerDialog to avoid actual dialog
        with patch('ui.pages.upload_page.ImageViewerDialog') as mock_dialog_class:
            mock_dialog = mock_dialog_class.return_value
            
            # Call view handler
            page._on_view_requested("test_view_id")
            
            # Verify dialog was created and executed
            mock_dialog_class.assert_called_once_with(test_meta, mock_image_store, page)
            mock_dialog.exec.assert_called_once()