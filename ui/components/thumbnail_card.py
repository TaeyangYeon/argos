"""
Thumbnail card component for displaying image previews in a grid layout.

This module provides the ThumbnailCard widget that shows image thumbnails
with metadata, type badges, and interactive features like hover states
and context menus.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QFont, QCursor, QMouseEvent
import numpy as np
import cv2

from core.image_store import ImageMeta, ImageType


class ThumbnailCard(QFrame):
    """
    Thumbnail card widget for displaying image previews with metadata.
    
    Features:
    - Image thumbnail preview (120×100px)
    - Type badge with color coding
    - Filename and dimensions display
    - Hover state with border highlighting
    - Context menu with view/delete options
    """
    
    # Signals
    view_requested = pyqtSignal(str)    # image_id
    delete_requested = pyqtSignal(str)  # image_id
    
    def __init__(self, meta: ImageMeta, parent=None):
        """
        Initialize the thumbnail card.
        
        Args:
            meta: ImageMeta instance with image data
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._meta = meta
        self._accent_colors = {
            ImageType.ALIGN_OK: "#1E88E5",
            ImageType.INSPECTION_OK: "#43A047",
            ImageType.INSPECTION_NG: "#E53935"
        }
        
        self._setup_ui()
        self._update_content()
        
    def _setup_ui(self) -> None:
        """Setup the thumbnail card UI layout."""
        # Set object name and size
        self.setObjectName("card")
        self.setFixedSize(140, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Image container with relative positioning for badge
        image_container = QWidget()
        image_container.setFixedSize(120, 100)
        
        # Image label
        self._image_label = QLabel(image_container)
        self._image_label.setFixedSize(120, 100)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: #16213E; border: 1px solid #2A2A4A; border-radius: 4px;")
        self._image_label.setScaledContents(True)
        
        # Type badge (overlaid on top-left of image)
        self._badge_label = QLabel(image_container)
        self._badge_label.setFixedHeight(20)
        self._badge_label.move(4, 4)  # Position in top-left corner
        badge_font = QFont()
        badge_font.setPointSize(9)
        badge_font.setBold(True)
        self._badge_label.setFont(badge_font)
        self._badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(image_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Filename label
        self._filename_label = QLabel()
        filename_font = QFont()
        filename_font.setPointSize(11)
        self._filename_label.setFont(filename_font)
        self._filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filename_label.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(self._filename_label)
        
        # Dimensions label
        self._dimensions_label = QLabel()
        dimensions_font = QFont()
        dimensions_font.setPointSize(10)
        self._dimensions_label.setFont(dimensions_font)
        self._dimensions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dimensions_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(self._dimensions_label)
        
        # Set default hover state
        self._is_hovered = False
        
    def _update_content(self) -> None:
        """Update the card content with current metadata."""
        # Update image thumbnail
        if self._meta.thumbnail is not None:
            pixmap = self._ndarray_to_pixmap(self._meta.thumbnail)
            scaled_pixmap = pixmap.scaled(
                120, 100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._image_label.setPixmap(scaled_pixmap)
        else:
            # Show placeholder if no thumbnail
            self._image_label.setText("No Preview")
            self._image_label.setStyleSheet(
                "background: #16213E; border: 1px solid #2A2A4A; "
                "border-radius: 4px; color: #9E9E9E;"
            )
            
        # Update filename (elided if too long)
        filename = Path(self._meta.file_path).name
        font_metrics = self._filename_label.fontMetrics()
        elided_filename = font_metrics.elidedText(
            filename, Qt.TextElideMode.ElideRight, 120
        )
        self._filename_label.setText(elided_filename)
        
        # Update dimensions
        self._dimensions_label.setText(f"{self._meta.width}×{self._meta.height}")
        
        # Update type badge
        accent_color = self._accent_colors[self._meta.image_type]
        badge_text = {
            ImageType.ALIGN_OK: "Align OK",
            ImageType.INSPECTION_OK: "OK",
            ImageType.INSPECTION_NG: "NG"
        }[self._meta.image_type]
        
        self._badge_label.setText(badge_text)
        self._badge_label.setStyleSheet(f"""
            QLabel {{
                background: {accent_color};
                color: #FFFFFF;
                border-radius: 10px;
                padding: 2px 8px;
            }}
        """)
        
        # Adjust badge width to fit text
        self._badge_label.adjustSize()
        
    def _ndarray_to_pixmap(self, arr: np.ndarray) -> QPixmap:
        """
        Convert OpenCV np.ndarray to QPixmap.
        
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
        
    def update_meta(self, meta: ImageMeta) -> None:
        """
        Update the card with new metadata.
        
        Args:
            meta: Updated ImageMeta instance
        """
        self._meta = meta
        self._update_content()
        
    def enterEvent(self, event) -> None:
        """Handle mouse enter events for hover state."""
        self._is_hovered = True
        accent_color = self._accent_colors[self._meta.image_type]
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: #1E2A4A;
                border: 1px solid {accent_color};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        super().enterEvent(event)
        
    def leaveEvent(self, event) -> None:
        """Handle mouse leave events to reset hover state."""
        self._is_hovered = False
        self.setStyleSheet("")  # Reset to default card styling
        super().leaveEvent(event)
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events for context menu."""
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)
        
    def _show_context_menu(self, position) -> None:
        """
        Show context menu at the given position.
        
        Args:
            position: Global position for menu display
        """
        menu = QMenu(self)
        
        # View action
        view_action = menu.addAction("🔍 크게 보기")
        view_action.triggered.connect(lambda: self.view_requested.emit(self._meta.id))
        
        # Delete action
        delete_action = menu.addAction("🗑 삭제")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self._meta.id))
        
        menu.exec(position)