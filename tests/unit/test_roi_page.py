"""
Unit tests for ROI page components.

This module tests the ROI canvas, controls, and page integration
to ensure proper functionality of the ROI selection system.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QPoint
from PyQt6.QtGui import QMouseEvent, QWheelEvent

from ui.components.roi_canvas import ROICanvas
from ui.components.roi_controls import ROIControls
from ui.pages.roi_page import ROIPage
from core.models import ROIConfig
from core.image_store import ImageStore, ImageType
from core.exceptions import InputValidationError


class TestROICanvas:
    """Test cases for ROICanvas component."""
    
    def test_roi_canvas_created(self, qtbot):
        """ROICanvas() instantiates without error."""
        canvas = ROICanvas()
        qtbot.addWidget(canvas)
        
        assert canvas is not None
        assert canvas.get_roi() is None
        assert canvas._image_array is None
        
    def test_load_image_sets_pixmap(self, qtbot):
        """load_image(np.zeros((480,640,3))) → canvas has non-null pixmap."""
        canvas = ROICanvas()
        qtbot.addWidget(canvas)
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas.load_image(test_image)
        
        assert canvas._image_array is not None
        assert canvas._original_width == 640
        assert canvas._original_height == 480
        
    def test_canvas_to_image_coords_center(self, qtbot):
        """Load 640×480 image, canvas 640×480 → center canvas coords map to ~(320, 240)."""
        canvas = ROICanvas()
        canvas.resize(640, 480)  # Set canvas size
        qtbot.addWidget(canvas)
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas.load_image(test_image)
        
        # Test center coordinates (approximately)
        img_x, img_y = canvas._canvas_to_image_coords(320, 240)
        
        # Should be roughly in the center (allowing for some letterboxing)
        assert 280 <= img_x <= 360  # Allow some tolerance
        assert 200 <= img_y <= 280
        
    def test_set_roi_triggers_repaint(self, qtbot):
        """set_roi(ROIConfig(10,10,100,100)) → get_roi() returns correct ROIConfig."""
        canvas = ROICanvas()
        qtbot.addWidget(canvas)
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas.load_image(test_image)
        
        # Set ROI
        test_roi = ROIConfig(10, 10, 100, 100)
        canvas.set_roi(test_roi)
        
        # Verify ROI is set
        current_roi = canvas.get_roi()
        assert current_roi is not None
        assert current_roi.x == 10
        assert current_roi.y == 10
        assert current_roi.width == 100
        assert current_roi.height == 100
        
    def test_clear_roi(self, qtbot):
        """set_roi then clear_roi → get_roi() is None."""
        canvas = ROICanvas()
        qtbot.addWidget(canvas)
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas.load_image(test_image)
        
        # Set then clear ROI
        test_roi = ROIConfig(10, 10, 100, 100)
        canvas.set_roi(test_roi)
        assert canvas.get_roi() is not None
        
        canvas.clear_roi()
        assert canvas.get_roi() is None
        
    def test_roi_changed_signal_on_draw(self, qtbot):
        """Simulate mouse press+move+release → roi_changed signal emitted."""
        canvas = ROICanvas()
        qtbot.addWidget(canvas)
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas.load_image(test_image)
        
        # Track signal emissions
        signal_emitted = []
        canvas.roi_changed.connect(lambda roi: signal_emitted.append(roi))
        
        # Simulate mouse drag
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(100, 100),
            QPointF(100, 100),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        canvas.mousePressEvent(press_event)
        
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(200, 200),
            QPointF(200, 200),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        canvas.mouseMoveEvent(move_event)
        
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(200, 200),
            QPointF(200, 200),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        canvas.mouseReleaseEvent(release_event)
        
        # Should have emitted ROI signal
        assert len(signal_emitted) == 1
        assert signal_emitted[0] is not None
        
    def test_zoom_functionality(self, qtbot):
        """Test zoom in/out with wheel events."""
        canvas = ROICanvas()
        qtbot.addWidget(canvas)
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas.load_image(test_image)
        
        initial_zoom = canvas._zoom_factor
        
        # Simulate zoom in
        wheel_event = QWheelEvent(
            QPointF(100, 100),  # position
            QPointF(100, 100),  # globalPosition
            QPoint(0, 0),       # pixelDelta
            QPoint(0, 120),     # angleDelta (positive for zoom in)
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False               # inverted
        )
        canvas.wheelEvent(wheel_event)
        
        assert canvas._zoom_factor > initial_zoom


class TestROIControls:
    """Test cases for ROIControls component."""
    
    def test_roi_controls_created(self, qtbot):
        """ROIControls() instantiates without error."""
        controls = ROIControls()
        qtbot.addWidget(controls)
        
        assert controls is not None
        assert controls._image_width == 0
        assert controls._image_height == 0
        
    def test_update_from_roi_updates_fields(self, qtbot):
        """update_from_roi(ROIConfig(10,20,100,200)) → spinboxes show 10, 20, 100, 200."""
        controls = ROIControls()
        qtbot.addWidget(controls)
        
        test_roi = ROIConfig(10, 20, 100, 200)
        controls.update_from_roi(test_roi)
        
        assert controls._x_spinbox.value() == 10
        assert controls._y_spinbox.value() == 20
        assert controls._width_spinbox.value() == 100
        assert controls._height_spinbox.value() == 200
        
    def test_get_roi_from_fields(self, qtbot):
        """Set spinbox values → get_roi_from_fields() returns matching ROIConfig."""
        controls = ROIControls()
        qtbot.addWidget(controls)
        
        # Set values
        controls._x_spinbox.setValue(15)
        controls._y_spinbox.setValue(25)
        controls._width_spinbox.setValue(150)
        controls._height_spinbox.setValue(250)
        
        roi = controls.get_roi_from_fields()
        
        assert roi.x == 15
        assert roi.y == 25
        assert roi.width == 150
        assert roi.height == 250
        
    def test_update_image_size_updates_label(self, qtbot):
        """update_image_size(640, 480) → label shows "640 × 480"."""
        controls = ROIControls()
        qtbot.addWidget(controls)
        
        controls.update_image_size(640, 480)
        
        assert "640 × 480" in controls._image_size_label.text()
        assert controls._image_width == 640
        assert controls._image_height == 480
        
    def test_roi_area_calculation(self, qtbot):
        """ROI area percentage calculation and color coding."""
        controls = ROIControls()
        qtbot.addWidget(controls)
        
        # Set image size
        controls.update_image_size(1000, 1000)
        
        # Set a large ROI (should be green)
        large_roi = ROIConfig(0, 0, 500, 500)  # 25% of image
        controls.update_from_roi(large_roi)
        
        assert "25.0%" in controls._roi_area_label.text()
        assert "#43A047" in controls._roi_area_label.styleSheet()  # Green
        
        # Set a small ROI (should be amber)
        small_roi = ROIConfig(0, 0, 50, 50)  # 0.25% of image (less than 1% threshold)
        controls.update_from_roi(small_roi)
        
        assert "0.2%" in controls._roi_area_label.text()
        assert "#FB8C00" in controls._roi_area_label.styleSheet()  # Amber
        
    def test_control_buttons(self, qtbot):
        """Test clear and full image buttons."""
        controls = ROIControls()
        qtbot.addWidget(controls)
        
        # Set image size
        controls.update_image_size(640, 480)
        
        # Track signal emissions
        signal_emitted = []
        controls.roi_updated.connect(lambda roi: signal_emitted.append(roi))
        
        # Test full image button
        controls._full_image_button.click()
        
        assert len(signal_emitted) == 1
        roi = signal_emitted[0]
        assert roi.x == 0
        assert roi.y == 0
        assert roi.width == 640
        assert roi.height == 480


class TestROIPage:
    """Test cases for ROIPage integration."""
    
    def test_roi_page_created(self, qtbot):
        """ROIPage with mock ImageStore → no error."""
        mock_image_store = MagicMock()
        mock_image_store.get_all.return_value = []
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        assert page is not None
        assert page._image_store == mock_image_store
        assert page.get_confirmed_roi() is None
        
    def test_roi_page_empty_state_no_images(self, qtbot):
        """Mock store.get_all() = [] → empty state message visible."""
        mock_image_store = MagicMock()
        mock_image_store.get_all.return_value = []
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Trigger refresh
        page.refresh_image_list()
        
        # Should show empty state
        assert page._content_stack.currentWidget() == page._empty_widget
        
    def test_roi_page_with_images(self, qtbot, make_image_meta):
        """Mock store with images → main interface visible."""
        mock_image_store = MagicMock()
        
        # Create test image
        test_meta = make_image_meta(ImageType.ALIGN_OK, "test.png", image_id="test1")
        mock_image_store.get_all.return_value = [test_meta]
        mock_image_store.get.return_value = test_meta
        mock_image_store.load_image.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Trigger refresh
        page.refresh_image_list()
        
        # Should show main interface
        assert page._content_stack.currentWidget() == page._main_widget
        
        # Should populate image selector
        assert page._image_selector.count() == 1
        
    def test_roi_confirmed_signal(self, qtbot, make_image_meta):
        """Mock valid ROI → click 확정 button → roi_confirmed signal emitted."""
        mock_image_store = MagicMock()
        
        # Create test image
        test_meta = make_image_meta(ImageType.ALIGN_OK, "test.png", image_id="test1", width=640, height=480)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        mock_image_store.get_all.return_value = [test_meta]
        mock_image_store.get.return_value = test_meta
        mock_image_store.load_image.return_value = test_image
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Set up page
        page.refresh_image_list()
        
        # Set a valid ROI
        test_roi = ROIConfig(50, 50, 200, 200)
        page._roi_canvas.set_roi(test_roi)
        
        # Track signal emissions
        signal_emitted = []
        page.roi_confirmed.connect(lambda roi: signal_emitted.append(roi))
        
        # Mock validation to pass
        with patch('core.validators.ROIValidator.validate_roi') as mock_validate:
            mock_validate.return_value = None  # No exception = validation passes
            
            # Mock toast to avoid actual display
            page._toast = MagicMock()
            
            # Click confirm button
            page._confirm_button.click()
            
            # Verify signal was emitted
            assert len(signal_emitted) == 1
            assert signal_emitted[0] == test_roi
            
    def test_roi_validation_error_shows_toast(self, qtbot, make_image_meta):
        """Mock ROIValidator to raise InputValidationError → click 확정 → error toast shown."""
        mock_image_store = MagicMock()
        
        # Create test image
        test_meta = make_image_meta(ImageType.ALIGN_OK, "test.png", image_id="test1")
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        mock_image_store.get_all.return_value = [test_meta]
        mock_image_store.get.return_value = test_meta
        mock_image_store.load_image.return_value = test_image
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Set up page
        page.refresh_image_list()
        
        # Set an ROI
        test_roi = ROIConfig(10, 10, 50, 50)
        page._roi_canvas.set_roi(test_roi)
        
        # Track signal emissions
        signal_emitted = []
        page.roi_confirmed.connect(lambda roi: signal_emitted.append(roi))
        
        # Mock validation to fail
        with patch('core.validators.ROIValidator.validate_roi') as mock_validate:
            mock_validate.side_effect = InputValidationError("ROI too small")
            
            # Mock toast to track calls
            page._toast = MagicMock()
            
            # Click confirm button
            page._confirm_button.click()
            
            # Verify error toast was shown
            page._toast.show_error.assert_called_once_with("ROI too small")
            
            # Verify no signal was emitted
            assert len(signal_emitted) == 0
            
    def test_get_confirmed_roi_after_confirm(self, qtbot, make_image_meta):
        """Confirm valid ROI → get_confirmed_roi() returns correct ROIConfig."""
        mock_image_store = MagicMock()
        
        # Create test image
        test_meta = make_image_meta(ImageType.ALIGN_OK, "test.png", image_id="test1", width=640, height=480)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        mock_image_store.get_all.return_value = [test_meta]
        mock_image_store.get.return_value = test_meta
        mock_image_store.load_image.return_value = test_image
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Set up page
        page.refresh_image_list()
        
        # Set a valid ROI
        test_roi = ROIConfig(100, 100, 300, 200)
        page._roi_canvas.set_roi(test_roi)
        
        # Mock validation to pass
        with patch('core.validators.ROIValidator.validate_roi') as mock_validate:
            mock_validate.return_value = None  # No exception = validation passes
            
            # Mock toast to avoid actual display
            page._toast = MagicMock()
            
            # Confirm ROI
            page._confirm_button.click()
            
            # Verify confirmed ROI matches
            confirmed_roi = page.get_confirmed_roi()
            assert confirmed_roi is not None
            assert confirmed_roi.x == test_roi.x
            assert confirmed_roi.y == test_roi.y
            assert confirmed_roi.width == test_roi.width
            assert confirmed_roi.height == test_roi.height
            
    def test_roi_sync_between_canvas_and_controls(self, qtbot, make_image_meta):
        """ROI changes sync bidirectionally between canvas and controls."""
        mock_image_store = MagicMock()
        
        # Create test image
        test_meta = make_image_meta(ImageType.ALIGN_OK, "test.png", image_id="test1")
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        mock_image_store.get_all.return_value = [test_meta]
        mock_image_store.get.return_value = test_meta
        mock_image_store.load_image.return_value = test_image
        
        page = ROIPage(mock_image_store)
        qtbot.addWidget(page)
        
        # Set up page
        page.refresh_image_list()
        
        # Test canvas → controls sync
        canvas_roi = ROIConfig(25, 35, 150, 200)
        page._roi_canvas.set_roi(canvas_roi)
        page._on_canvas_roi_changed(canvas_roi)
        
        # Controls should be updated
        assert page._roi_controls._x_spinbox.value() == 25
        assert page._roi_controls._y_spinbox.value() == 35
        assert page._roi_controls._width_spinbox.value() == 150
        assert page._roi_controls._height_spinbox.value() == 200
        
        # Test controls → canvas sync
        controls_roi = ROIConfig(50, 75, 180, 120)
        page._on_controls_roi_updated(controls_roi)
        
        # Canvas should be updated
        canvas_current_roi = page._roi_canvas.get_roi()
        assert canvas_current_roi.x == 50
        assert canvas_current_roi.y == 75
        assert canvas_current_roi.width == 180
        assert canvas_current_roi.height == 120