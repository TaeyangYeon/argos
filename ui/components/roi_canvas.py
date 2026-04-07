"""
Interactive ROI canvas component for mouse-driven region selection.

This module provides the ROICanvas widget that displays an image with
an interactive ROI overlay, supporting mouse drag selection, zoom,
and real-time coordinate mapping.
"""

import numpy as np
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont, QWheelEvent, QMouseEvent
import cv2

from core.models import ROIConfig


class ROICanvas(QLabel):
    """
    Interactive canvas for displaying images with ROI selection overlay.
    
    Features:
    - Image display with aspect ratio preservation
    - Mouse drag ROI selection
    - Real-time coordinate mapping between canvas and image coordinates
    - Zoom functionality with mouse wheel
    - ROI visualization with corner handles and size label
    """
    
    # Signal emitted when ROI changes
    roi_changed = pyqtSignal(object)  # ROIConfig or None
    
    def __init__(self, parent=None):
        """
        Initialize the ROI canvas.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Image data
        self._image_array = None
        self._display_pixmap = None
        self._original_width = 0
        self._original_height = 0
        
        # Display properties
        self._scale_factor = 1.0
        self._zoom_factor = 1.0
        self._offset_x = 0
        self._offset_y = 0
        
        # ROI state
        self._current_roi = None
        self._drag_start_point = None
        self._drag_end_point = None
        self._is_dragging = False
        
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Setup the canvas UI properties."""
        self.setMinimumSize(600, 400)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
            }
        """)
        
        # Enable mouse tracking and set cursor
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def load_image(self, image: np.ndarray) -> None:
        """
        Load an image into the canvas.
        
        Args:
            image: NumPy array representing the image (BGR format)
        """
        if image is None or image.size == 0:
            self._image_array = None
            self._display_pixmap = None
            self.clear()
            return
            
        self._image_array = image.copy()
        self._original_height, self._original_width = image.shape[:2]
        
        # Reset zoom and ROI
        self._zoom_factor = 1.0
        self._current_roi = None
        
        self._update_display_pixmap()
        self.update()
        
    def _update_display_pixmap(self) -> None:
        """Update the display pixmap with current zoom level."""
        if self._image_array is None:
            return
            
        # Convert to QPixmap
        pixmap = self._ndarray_to_pixmap(self._image_array)
        
        # Calculate display size with zoom
        canvas_size = self.size()
        image_size = pixmap.size()
        
        # Scale to fit canvas while preserving aspect ratio
        scaled_size = image_size.scaled(
            canvas_size, 
            Qt.AspectRatioMode.KeepAspectRatio
        )
        
        # Apply zoom factor
        zoomed_size = scaled_size * self._zoom_factor
        
        # Calculate scale factor and offset for coordinate mapping
        self._scale_factor = min(
            zoomed_size.width() / self._original_width,
            zoomed_size.height() / self._original_height
        )
        
        # Calculate letterbox offset
        self._offset_x = max(0, (canvas_size.width() - zoomed_size.width()) // 2)
        self._offset_y = max(0, (canvas_size.height() - zoomed_size.height()) // 2)
        
        # Scale pixmap
        self._display_pixmap = pixmap.scaled(
            zoomed_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.setPixmap(self._display_pixmap)
        
    def _ndarray_to_pixmap(self, arr: np.ndarray) -> QPixmap:
        """
        Convert NumPy array to QPixmap.
        
        Args:
            arr: NumPy array (BGR color or grayscale)
            
        Returns:
            QPixmap for display
        """
        if len(arr.shape) == 2:
            # Grayscale image
            height, width = arr.shape
            bytes_per_line = width
            qimage = QImage(
                arr.data, width, height, bytes_per_line,
                QImage.Format.Format_Grayscale8
            )
        else:
            # Color image (BGR -> RGB)
            rgb_arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_arr.shape
            bytes_per_line = channels * width
            qimage = QImage(
                rgb_arr.data, width, height, bytes_per_line,
                QImage.Format.Format_RGB888
            )
            
        return QPixmap.fromImage(qimage)
        
    def _canvas_to_image_coords(self, canvas_x: int, canvas_y: int) -> tuple[int, int]:
        """
        Convert canvas pixel coordinates to original image coordinates.
        
        Args:
            canvas_x: X coordinate on canvas
            canvas_y: Y coordinate on canvas
            
        Returns:
            Tuple of (x, y) in image coordinates
        """
        if self._image_array is None or self._scale_factor == 0:
            return (0, 0)
            
        # Account for letterbox offset
        image_x = (canvas_x - self._offset_x) / self._scale_factor
        image_y = (canvas_y - self._offset_y) / self._scale_factor
        
        # Clamp to image boundaries
        image_x = max(0, min(int(image_x), self._original_width - 1))
        image_y = max(0, min(int(image_y), self._original_height - 1))
        
        return (image_x, image_y)
        
    def _image_to_canvas_coords(self, img_x: int, img_y: int) -> tuple[int, int]:
        """
        Convert image coordinates to canvas pixel coordinates.
        
        Args:
            img_x: X coordinate in image
            img_y: Y coordinate in image
            
        Returns:
            Tuple of (x, y) in canvas coordinates
        """
        if self._image_array is None:
            return (0, 0)
            
        canvas_x = int(img_x * self._scale_factor + self._offset_x)
        canvas_y = int(img_y * self._scale_factor + self._offset_y)
        
        return (canvas_x, canvas_y)
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events to start ROI drag."""
        if event.button() == Qt.MouseButton.LeftButton and self._image_array is not None:
            self._is_dragging = True
            canvas_pos = event.position().toPoint()
            self._drag_start_point = self._canvas_to_image_coords(canvas_pos.x(), canvas_pos.y())
            self._drag_end_point = self._drag_start_point
            
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move events to update ROI rectangle."""
        if self._is_dragging and self._image_array is not None:
            canvas_pos = event.position().toPoint()
            self._drag_end_point = self._canvas_to_image_coords(canvas_pos.x(), canvas_pos.y())
            self.update()  # Trigger repaint
            
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events to finalize ROI."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            
            if self._drag_start_point and self._drag_end_point:
                # Calculate ROI rectangle
                x1, y1 = self._drag_start_point
                x2, y2 = self._drag_end_point
                
                # Ensure positive width/height
                x = min(x1, x2)
                y = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                # Only create ROI if it has reasonable size
                if width > 5 and height > 5:
                    # Clamp to image boundaries
                    x = max(0, min(x, self._original_width - 1))
                    y = max(0, min(y, self._original_height - 1))
                    width = min(width, self._original_width - x)
                    height = min(height, self._original_height - y)
                    
                    self._current_roi = ROIConfig(x, y, width, height)
                    self.roi_changed.emit(self._current_roi)
                else:
                    # Clear ROI if too small
                    self._current_roi = None
                    self.roi_changed.emit(None)
                    
            self._drag_start_point = None
            self._drag_end_point = None
            self.update()
            
        super().mouseReleaseEvent(event)
        
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel events for zoom."""
        if self._image_array is None:
            event.accept()
            return
            
        # Calculate zoom change
        delta = event.angleDelta().y()
        zoom_change = 1.1 if delta > 0 else 0.9
        
        new_zoom = self._zoom_factor * zoom_change
        new_zoom = max(0.25, min(4.0, new_zoom))  # Clamp zoom range
        
        if new_zoom != self._zoom_factor:
            self._zoom_factor = new_zoom
            self._update_display_pixmap()
            self.update()
            
        event.accept()
        
    def paintEvent(self, event) -> None:
        """Custom paint event to draw ROI overlay."""
        super().paintEvent(event)
        
        if self._image_array is None:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw current ROI or drag preview
        roi_to_draw = None
        
        if self._is_dragging and self._drag_start_point and self._drag_end_point:
            # Draw drag preview
            x1, y1 = self._drag_start_point
            x2, y2 = self._drag_end_point
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            roi_to_draw = ROIConfig(x, y, width, height)
        elif self._current_roi:
            roi_to_draw = self._current_roi
            
        if roi_to_draw:
            self._draw_roi_overlay(painter, roi_to_draw)
            
        painter.end()
        
    def _draw_roi_overlay(self, painter: QPainter, roi: ROIConfig) -> None:
        """
        Draw ROI overlay on the canvas.
        
        Args:
            painter: QPainter instance
            roi: ROI configuration to draw
        """
        # Convert ROI coordinates to canvas coordinates
        x1, y1 = self._image_to_canvas_coords(roi.x, roi.y)
        x2, y2 = self._image_to_canvas_coords(roi.x + roi.width, roi.y + roi.height)
        
        rect = QRect(x1, y1, x2 - x1, y2 - y1)
        
        # Draw semi-transparent fill
        brush = QBrush(QColor(30, 136, 229, 51))  # #1E88E5 at 20% opacity
        painter.fillRect(rect, brush)
        
        # Draw solid border
        pen = QPen(QColor(30, 136, 229), 2)  # #1E88E5, 2px
        painter.setPen(pen)
        painter.drawRect(rect)
        
        # Draw corner handles
        handle_size = 8
        handle_color = QColor(30, 136, 229)
        painter.fillRect(x1 - handle_size//2, y1 - handle_size//2, handle_size, handle_size, handle_color)
        painter.fillRect(x2 - handle_size//2, y1 - handle_size//2, handle_size, handle_size, handle_color)
        painter.fillRect(x1 - handle_size//2, y2 - handle_size//2, handle_size, handle_size, handle_color)
        painter.fillRect(x2 - handle_size//2, y2 - handle_size//2, handle_size, handle_size, handle_color)
        
        # Draw size label inside ROI (if it's large enough)
        if rect.width() > 80 and rect.height() > 30:
            label_text = f"{roi.width} × {roi.height}"
            
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            
            # White text with black outline for visibility
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            
            # Center the text in the ROI
            text_rect = painter.fontMetrics().boundingRect(label_text)
            text_x = rect.center().x() - text_rect.width() // 2
            text_y = rect.center().y() + text_rect.height() // 2
            
            painter.drawText(text_x, text_y, label_text)
            
    def set_roi(self, roi: ROIConfig) -> None:
        """
        Set ROI from external source.
        
        Args:
            roi: ROI configuration to set
        """
        self._current_roi = roi
        self.update()
        
    def get_roi(self) -> ROIConfig | None:
        """
        Get current ROI configuration.
        
        Returns:
            Current ROIConfig or None if no ROI is set
        """
        return self._current_roi
        
    def clear_roi(self) -> None:
        """Clear current ROI and trigger repaint."""
        self._current_roi = None
        self.update()
        
    def set_zoom(self, factor: float) -> None:
        """
        Set zoom factor.
        
        Args:
            factor: Zoom factor (0.25 to 4.0)
        """
        factor = max(0.25, min(4.0, factor))
        if factor != self._zoom_factor:
            self._zoom_factor = factor
            self._update_display_pixmap()
            self.update()
            
    def fit_to_window(self) -> None:
        """Reset zoom to fit image in canvas."""
        self.set_zoom(1.0)