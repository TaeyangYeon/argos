"""
Unit tests for upload page components.

This module tests the upload page, drop zones, and toast messages
to ensure proper functionality and file handling.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtTest import QTest

from ui.components.drop_zone import DropZone
from ui.components.toast import ToastMessage
from ui.pages.upload_page import UploadPage
from core.image_store import ImageStore, ImageType
from core.validators import ImageValidator
from core.exceptions import InputValidationError


class TestDropZone:
    """Test cases for DropZone component."""
    
    def test_drop_zone_created(self, qtbot):
        """DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5") instantiates without error."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        assert drop_zone is not None
        assert drop_zone.get_image_type() == ImageType.ALIGN_OK
        assert drop_zone._label == "Align OK"
        assert drop_zone._accent_color == "#1E88E5"
        
    def test_drop_zone_count_badge_initial(self, qtbot):
        """Initial count badge shows "0장"."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        assert drop_zone._count_badge.text() == "0장"
        assert drop_zone._count == 0
        
    def test_drop_zone_update_count(self, qtbot):
        """update_count(3) → badge shows "3장"."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        drop_zone.update_count(3)
        
        assert drop_zone._count_badge.text() == "3장"
        assert drop_zone._count == 3
        
        # Check styling changes for non-zero count
        badge_style = drop_zone._count_badge.styleSheet()
        assert "#1E88E5" in badge_style  # Accent color background
        assert "#FFFFFF" in badge_style  # White text
        
        # Test zero count
        drop_zone.update_count(0)
        assert drop_zone._count_badge.text() == "0장"
        badge_style = drop_zone._count_badge.styleSheet()
        assert "transparent" in badge_style  # Transparent background
        assert "#9E9E9E" in badge_style  # Muted text
        
    def test_drop_zone_emits_signal_on_valid_drop(self, qtbot):
        """Simulate drop event with valid file path → files_dropped signal emitted with path list."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        # Connect signal to track emissions
        files_dropped = []
        drop_zone.files_dropped.connect(lambda files: files_dropped.extend(files))
        
        # Create mock drop event with valid image file
        mock_event = MagicMock()
        mock_mime_data = MagicMock()
        mock_url = MagicMock()
        mock_url.toLocalFile.return_value = "/test/path/image.png"
        
        mock_mime_data.urls.return_value = [mock_url]
        mock_event.mimeData.return_value = mock_mime_data
        mock_event.acceptProposedAction.return_value = None
        
        # Trigger drop event
        drop_zone.dropEvent(mock_event)
        
        # Verify signal was emitted with correct path
        assert len(files_dropped) == 1
        assert files_dropped[0] == "/test/path/image.png"
        
    def test_drop_zone_set_error_state(self, qtbot):
        """set_error_state() briefly flashes error state."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        # Initially default state
        assert drop_zone._state == "default"
        
        # Set error state
        drop_zone.set_error_state("Test error")
        
        # Should be in error state
        assert drop_zone._state == "error"
        
        # After timer, should reset (we can't easily test the timer, but the method exists)
        assert hasattr(drop_zone, '_reset_state')
        
    def test_drop_zone_hover_states(self, qtbot):
        """Test hover enter/leave state changes."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        # Initially default
        assert drop_zone._state == "default"
        
        # Simulate mouse enter
        drop_zone.enterEvent(None)
        assert drop_zone._state == "hover"
        
        # Simulate mouse leave
        drop_zone.leaveEvent(None)
        assert drop_zone._state == "default"
        
    def test_drop_zone_file_dialog(self, qtbot):
        """Click drop zone → opens file dialog."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        # Connect signal to track emissions
        files_dropped = []
        drop_zone.files_dropped.connect(lambda files: files_dropped.extend(files))
        
        # Mock QFileDialog to return test files
        with patch('ui.components.drop_zone.QFileDialog.getOpenFileNames') as mock_dialog:
            mock_dialog.return_value = (["/test1.png", "/test2.jpg"], "")
            
            # Simulate click
            qtbot.mouseClick(drop_zone, Qt.MouseButton.LeftButton)
            
            # Verify dialog was called and signal emitted
            mock_dialog.assert_called_once()
            assert len(files_dropped) == 2
            assert files_dropped == ["/test1.png", "/test2.jpg"]
            
    def test_drop_zone_drag_enter_valid_files(self, qtbot):
        """Drag enter with valid image files → accept event."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        # Create mock drag enter event
        mock_event = MagicMock()
        mock_mime_data = MagicMock()
        mock_mime_data.hasUrls.return_value = True
        mock_url = MagicMock()
        mock_url.toLocalFile.return_value = "/test/image.png"
        mock_mime_data.urls.return_value = [mock_url]
        mock_event.mimeData.return_value = mock_mime_data
        
        drop_zone.dragEnterEvent(mock_event)
        
        # Should accept and change to drag_over state
        mock_event.acceptProposedAction.assert_called_once()
        assert drop_zone._state == "drag_over"
        
    def test_drop_zone_drag_enter_invalid_files(self, qtbot):
        """Drag enter with invalid files → ignore event."""
        drop_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        qtbot.addWidget(drop_zone)
        
        # Create mock drag enter event with invalid file
        mock_event = MagicMock()
        mock_mime_data = MagicMock()
        mock_mime_data.hasUrls.return_value = True
        mock_url = MagicMock()
        mock_url.toLocalFile.return_value = "/test/document.txt"  # Not an image
        mock_mime_data.urls.return_value = [mock_url]
        mock_event.mimeData.return_value = mock_mime_data
        
        drop_zone.dragEnterEvent(mock_event)
        
        # Should ignore
        mock_event.ignore.assert_called_once()
        assert drop_zone._state == "default"


class TestToastMessage:
    """Test cases for ToastMessage component."""
    
    def test_toast_show_success(self, qtbot):
        """ToastMessage.show_success("test") → no error."""
        from PyQt6.QtWidgets import QWidget
        parent = QWidget()
        
        toast = ToastMessage(parent)
        qtbot.addWidget(toast)
        
        # Should not raise any errors
        toast.show_success("Test success message")
        
        assert toast._icon_label.text() == "✅"
        assert toast._message_label.text() == "Test success message"
        assert "#43A047" in toast.styleSheet()  # Success color
        
    def test_toast_show_error(self, qtbot):
        """ToastMessage.show_error("test") → no error."""
        from PyQt6.QtWidgets import QWidget
        parent = QWidget()
        
        toast = ToastMessage(parent)
        qtbot.addWidget(toast)
        
        # Should not raise any errors
        toast.show_error("Test error message")
        
        assert toast._icon_label.text() == "❌"
        assert toast._message_label.text() == "Test error message"
        assert "#E53935" in toast.styleSheet()  # Error color
        
    def test_toast_show_warning(self, qtbot):
        """ToastMessage.show_warning("test") → no error."""
        from PyQt6.QtWidgets import QWidget
        parent = QWidget()
        
        toast = ToastMessage(parent)
        qtbot.addWidget(toast)
        
        # Should not raise any errors
        toast.show_warning("Test warning message")
        
        assert toast._icon_label.text() == "⚠️"
        assert toast._message_label.text() == "Test warning message"
        assert "#FB8C00" in toast.styleSheet()  # Warning color
        
    def test_toast_close_button(self, qtbot):
        """Close button hides toast."""
        toast = ToastMessage()
        qtbot.addWidget(toast)
        
        # Show and then click close
        toast.show()
        assert toast.isVisible()
        
        qtbot.mouseClick(toast._close_button, Qt.MouseButton.LeftButton)
        assert not toast.isVisible()


class TestUploadPage:
    """Test cases for UploadPage."""
    
    def test_upload_page_created(self, qtbot):
        """UploadPage with mock ImageStore → no error."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        assert page is not None
        assert page._image_store == mock_image_store
        
    def test_upload_page_has_three_drop_zones(self, qtbot):
        """Page contains exactly 3 DropZone instances."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Check that 3 drop zones were created
        assert page._align_ok_zone is not None
        assert page._inspection_ok_zone is not None
        assert page._inspection_ng_zone is not None
        
        # Check they are DropZone instances
        assert isinstance(page._align_ok_zone, DropZone)
        assert isinstance(page._inspection_ok_zone, DropZone)
        assert isinstance(page._inspection_ng_zone, DropZone)
        
        # Check correct image types
        assert page._align_ok_zone.get_image_type() == ImageType.ALIGN_OK
        assert page._inspection_ok_zone.get_image_type() == ImageType.INSPECTION_OK
        assert page._inspection_ng_zone.get_image_type() == ImageType.INSPECTION_NG
        
    def test_ng_warning_hidden_initially(self, qtbot):
        """NG warning banner is hidden on init."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        assert page._ng_warning_banner is not None
        assert not page._ng_warning_banner.isVisible()
        
    def test_ng_warning_visible_when_ok_exists_ng_zero(self, qtbot):
        """Mock store: OK=1, NG=0 → banner visible after refresh."""
        mock_image_store = MagicMock()
        mock_image_store.count.side_effect = lambda image_type=None: {
            ImageType.ALIGN_OK: 0,
            ImageType.INSPECTION_OK: 1,
            ImageType.INSPECTION_NG: 0,
            None: 1
        }.get(image_type, 0)
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Ensure the page is shown to trigger proper initialization
        page.show()
        qtbot.waitExposed(page)
        
        page._refresh_ui()
        
        assert page._ng_warning_banner.isVisible()
        warning_text = page._warning_text_label.text()
        assert "NG 이미지가 필요합니다" in warning_text
        assert "현재 등록: OK 1장 / NG 0장" in warning_text
        
    def test_ng_warning_hidden_when_ng_exists(self, qtbot):
        """Mock store: OK=1, NG=1 → banner hidden after refresh."""
        mock_image_store = MagicMock()
        mock_image_store.count.side_effect = lambda image_type=None: {
            ImageType.ALIGN_OK: 0,
            ImageType.INSPECTION_OK: 1,
            ImageType.INSPECTION_NG: 1,
            None: 2
        }.get(image_type, 0)
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        page._refresh_ui()
        
        assert not page._ng_warning_banner.isVisible()
        
    def test_refresh_updates_drop_zone_counts(self, qtbot):
        """Mock store counts → after _refresh_ui() → drop zone badges updated."""
        mock_image_store = MagicMock()
        mock_image_store.count.side_effect = lambda image_type=None: {
            ImageType.ALIGN_OK: 2,
            ImageType.INSPECTION_OK: 3,
            ImageType.INSPECTION_NG: 1,
            None: 6
        }.get(image_type, 0)
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        page._refresh_ui()
        
        # Check drop zone counts
        assert page._align_ok_zone._count_badge.text() == "2장"
        assert page._inspection_ok_zone._count_badge.text() == "3장"
        assert page._inspection_ng_zone._count_badge.text() == "1장"
        
        # Check summary labels
        assert "Align OK: 2장" in page._summary_labels["align_ok"].text()
        assert "Inspection OK: 3장" in page._summary_labels["inspection_ok"].text()
        assert "Inspection NG: 1장" in page._summary_labels["inspection_ng"].text()
        assert "전체: 6장" in page._summary_labels["total"].text()
        
    def test_images_updated_signal_emitted_on_add(self, qtbot):
        """Mock successful image_store.add() → images_updated signal emitted."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Connect signal to track emissions
        signal_emitted = []
        page.images_updated.connect(lambda: signal_emitted.append(True))
        
        # Mock successful validation and addition
        with patch('ui.pages.upload_page.ImageValidator.validate_image') as mock_validator:
            mock_validator.return_value = MagicMock()  # Valid image
            
            # Simulate file drop
            page._handle_files_dropped(["/test/image.png"], ImageType.ALIGN_OK)
            
            # Verify signal was emitted
            assert len(signal_emitted) == 1
            
            # Verify store.add was called
            mock_image_store.add.assert_called_once_with("/test/image.png", ImageType.ALIGN_OK)
            
    def test_invalid_file_shows_error_toast(self, qtbot):
        """Mock ImageValidator to raise InputValidationError → verify set_error_state called on drop_zone."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Mock validator to raise error
        with patch('ui.pages.upload_page.ImageValidator.validate_image') as mock_validator:
            mock_validator.side_effect = InputValidationError("Invalid image format")
            
            # Mock the drop zone's set_error_state method
            page._align_ok_zone.set_error_state = MagicMock()
            
            # Mock toast to avoid actual display
            page._toast.show_error = MagicMock()
            
            # Simulate file drop
            page._handle_files_dropped(["/test/invalid.txt"], ImageType.ALIGN_OK)
            
            # Verify error handling
            page._align_ok_zone.set_error_state.assert_called_once_with("Invalid image format")
            page._toast.show_error.assert_called_once_with("Invalid image format")
            
            # Verify store.add was NOT called
            mock_image_store.add.assert_not_called()
            
    def test_clear_all_with_confirmation(self, qtbot):
        """전체 초기화 button → confirmation dialog → clear store."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 5
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Connect signal to track emissions
        signal_emitted = []
        page.images_updated.connect(lambda: signal_emitted.append(True))
        
        # Mock toast to avoid actual display
        page._toast.show_success = MagicMock()
        
        # Mock QMessageBox.exec to return Yes
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
            # Click clear button
            page._handle_clear_all()
            
            # Verify store was cleared
            mock_image_store.clear.assert_called_once()
            
            # Verify signal was emitted
            assert len(signal_emitted) == 1
            
            # Verify success toast
            page._toast.show_success.assert_called_once_with("전체 초기화 완료")
            
    def test_clear_all_canceled(self, qtbot):
        """전체 초기화 button → cancel confirmation → no action."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 5
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Connect signal to track emissions
        signal_emitted = []
        page.images_updated.connect(lambda: signal_emitted.append(True))
        
        # Mock QMessageBox.exec to return No
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.No):
            # Click clear button
            page._handle_clear_all()
            
            # Verify store was NOT cleared
            mock_image_store.clear.assert_not_called()
            
            # Verify signal was NOT emitted
            assert len(signal_emitted) == 0
            
    def test_upload_page_toast_exists(self, qtbot):
        """Upload page has toast message component."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        assert page._toast is not None
        assert isinstance(page._toast, ToastMessage)
        
    def test_upload_page_clear_button_exists(self, qtbot):
        """Upload page has clear button with correct styling."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        assert page._clear_button is not None
        assert "전체 초기화" in page._clear_button.text()
        assert page._clear_button.objectName() == "dangerBtn"
        
    def test_upload_page_show_event_calls_refresh(self, qtbot):
        """showEvent triggers _refresh_ui() automatically."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        
        page = UploadPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Mock refresh method to track calls
        refresh_called = []
        original_refresh = page._refresh_ui
        
        def mock_refresh():
            refresh_called.append(True)
            original_refresh()
            
        page._refresh_ui = mock_refresh
        
        # Show the widget to trigger showEvent
        page.show()
        
        # Verify refresh was called
        assert len(refresh_called) > 0