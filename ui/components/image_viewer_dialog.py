"""
Image viewer dialog for displaying full-size image previews.

This module provides the ImageViewerDialog widget that shows a modal
dialog with the full-resolution image and metadata information.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QFont
import numpy as np
import cv2

from core.image_store import ImageMeta, ImageStore, ImageType
from ui.components.thumbnail_card import ThumbnailCard  # For _ndarray_to_pixmap method


class ImageViewerDialog(QDialog):
    """
    Modal dialog for full-size image preview with metadata.
    
    Features:
    - Full-size image display scaled to fit dialog
    - Type badge and filename header
    - Image metadata (dimensions, file size)
    - Added timestamp information
    - Close button
    """
    
    def __init__(self, meta: ImageMeta, image_store: ImageStore, parent=None):
        """
        Initialize the image viewer dialog.
        
        Args:
            meta: ImageMeta instance with image data
            image_store: ImageStore for loading full-resolution image
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._meta = meta
        self._image_store = image_store
        self._accent_colors = {
            ImageType.ALIGN_OK: "#1E88E5",
            ImageType.INSPECTION_OK: "#43A047",
            ImageType.INSPECTION_NG: "#E53935"
        }
        
        self._setup_ui()
        self._load_and_display_image()
        
    def _setup_ui(self) -> None:
        """Setup the image viewer dialog UI."""
        # Set dialog properties
        filename = Path(self._meta.file_path).name
        self.setWindowTitle(filename)
        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header section
        header_layout = QHBoxLayout()
        
        # Type badge
        badge_text = {
            ImageType.ALIGN_OK: "Align OK",
            ImageType.INSPECTION_OK: "OK",
            ImageType.INSPECTION_NG: "NG"
        }[self._meta.image_type]
        
        self._badge_label = QLabel(badge_text)
        badge_font = QFont()
        badge_font.setPointSize(10)
        badge_font.setBold(True)
        self._badge_label.setFont(badge_font)
        self._badge_label.setFixedHeight(24)
        
        accent_color = self._accent_colors[self._meta.image_type]
        self._badge_label.setStyleSheet(f"""
            QLabel {{
                background: {accent_color};
                color: #FFFFFF;
                border-radius: 12px;
                padding: 4px 12px;
            }}
        """)
        self._badge_label.adjustSize()
        
        # Filename
        self._filename_label = QLabel(filename)
        filename_font = QFont()
        filename_font.setPointSize(16)
        filename_font.setBold(True)
        self._filename_label.setFont(filename_font)
        self._filename_label.setStyleSheet("color: #E0E0E0;")
        
        header_layout.addWidget(self._badge_label)
        header_layout.addWidget(self._filename_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Metadata row
        metadata_layout = QHBoxLayout()
        
        # Dimensions and file size
        file_size_kb = self._meta.file_size_bytes / 1024
        metadata_text = f"{self._meta.width}×{self._meta.height} | {file_size_kb:.1f} KB"
        
        self._metadata_label = QLabel(metadata_text)
        metadata_font = QFont()
        metadata_font.setPointSize(12)
        self._metadata_label.setFont(metadata_font)
        self._metadata_label.setStyleSheet("color: #9E9E9E;")
        
        metadata_layout.addWidget(self._metadata_label)
        metadata_layout.addStretch()
        
        layout.addLayout(metadata_layout)
        
        # Image display area
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("""
            QLabel {
                background: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
            }
        """)
        self._image_label.setScaledContents(False)  # We'll handle scaling manually
        
        layout.addWidget(self._image_label, 1)  # Give it stretch
        
        # Footer section
        footer_layout = QHBoxLayout()
        
        # Added timestamp
        added_label = QLabel(f"Added: {self._meta.added_at}")
        added_font = QFont()
        added_font.setPointSize(11)
        added_label.setFont(added_font)
        added_label.setStyleSheet("color: #9E9E9E;")
        
        # Close button
        close_button = QPushButton("닫기")
        close_button.setObjectName("primaryBtn")
        close_button.clicked.connect(self.accept)
        close_button.setFixedWidth(80)
        
        footer_layout.addWidget(added_label)
        footer_layout.addStretch()
        footer_layout.addWidget(close_button)
        
        layout.addLayout(footer_layout)
        
    def _load_and_display_image(self) -> None:
        """Load the full-resolution image and display it."""
        try:
            # Load full-resolution image from store
            image_array = self._image_store.load_image(self._meta.id)
            
            if image_array is not None:
                # Convert to QPixmap
                pixmap = self._ndarray_to_pixmap(image_array)
                
                # Scale to fit the image label while keeping aspect ratio
                label_size = self._image_label.size()
                if label_size.width() > 0 and label_size.height() > 0:
                    scaled_pixmap = pixmap.scaled(
                        label_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self._image_label.setPixmap(scaled_pixmap)
                else:
                    # If label size is not available yet, use original size
                    self._image_label.setPixmap(pixmap)
            else:
                # Show error message
                self._image_label.setText("Failed to load image")
                self._image_label.setStyleSheet("""
                    QLabel {
                        background: #16213E;
                        border: 1px solid #E53935;
                        border-radius: 8px;
                        color: #E53935;
                        font-size: 16px;
                    }
                """)
                
        except Exception as e:
            # Show error message
            self._image_label.setText(f"Error loading image: {str(e)}")
            self._image_label.setStyleSheet("""
                QLabel {
                    background: #16213E;
                    border: 1px solid #E53935;
                    border-radius: 8px;
                    color: #E53935;
                    font-size: 14px;
                }
            """)
            
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
        
    def resizeEvent(self, event) -> None:
        """Handle dialog resize to rescale the image."""
        super().resizeEvent(event)
        
        # Re-load and scale the image when dialog is resized
        if hasattr(self, '_meta') and hasattr(self, '_image_store'):
            # Small delay to ensure layout is updated
            self._load_and_display_image()