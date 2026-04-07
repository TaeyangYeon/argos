"""
ROI coordinate controls component for manual ROI input and configuration.

This module provides the ROIControls widget that displays coordinate input
fields, image information, and control buttons for ROI management.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.models import ROIConfig
from config.constants import MIN_ROI_AREA_RATIO


class ROIControls(QFrame):
    """
    ROI coordinate input and control panel.
    
    Features:
    - Coordinate input fields (X, Y, Width, Height)
    - Image size display
    - ROI area percentage calculation
    - Control buttons (Clear, Full Image)
    - Bidirectional sync with ROI canvas
    """
    
    # Signal emitted when ROI is updated from controls
    roi_updated = pyqtSignal(object)  # ROIConfig
    
    def __init__(self, parent=None):
        """
        Initialize the ROI controls panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Image dimensions
        self._image_width = 0
        self._image_height = 0
        
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Setup the ROI controls UI."""
        self.setObjectName("card")
        self.setFixedWidth(220)
        
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title_label = QLabel("ROI 좌표 설정")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(title_label)
        
        # Coordinate input grid
        coord_layout = QGridLayout()
        coord_layout.setSpacing(8)
        
        # X coordinate
        x_label = QLabel("X")
        x_label.setStyleSheet("color: #9E9E9E; font-weight: 500;")
        self._x_spinbox = QSpinBox()
        self._x_spinbox.setRange(0, 99999)
        self._x_spinbox.valueChanged.connect(self._on_coordinate_changed)
        coord_layout.addWidget(x_label, 0, 0)
        coord_layout.addWidget(self._x_spinbox, 1, 0)
        
        # Y coordinate
        y_label = QLabel("Y")
        y_label.setStyleSheet("color: #9E9E9E; font-weight: 500;")
        self._y_spinbox = QSpinBox()
        self._y_spinbox.setRange(0, 99999)
        self._y_spinbox.valueChanged.connect(self._on_coordinate_changed)
        coord_layout.addWidget(y_label, 0, 1)
        coord_layout.addWidget(self._y_spinbox, 1, 1)
        
        # Width
        width_label = QLabel("Width")
        width_label.setStyleSheet("color: #9E9E9E; font-weight: 500;")
        self._width_spinbox = QSpinBox()
        self._width_spinbox.setRange(0, 99999)
        self._width_spinbox.valueChanged.connect(self._on_coordinate_changed)
        coord_layout.addWidget(width_label, 2, 0)
        coord_layout.addWidget(self._width_spinbox, 3, 0)
        
        # Height
        height_label = QLabel("Height")
        height_label.setStyleSheet("color: #9E9E9E; font-weight: 500;")
        self._height_spinbox = QSpinBox()
        self._height_spinbox.setRange(0, 99999)
        self._height_spinbox.valueChanged.connect(self._on_coordinate_changed)
        coord_layout.addWidget(height_label, 2, 1)
        coord_layout.addWidget(self._height_spinbox, 3, 1)
        
        layout.addLayout(coord_layout)
        
        # Image size info
        self._image_size_label = QLabel("이미지 크기: 0 × 0")
        self._image_size_label.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        layout.addWidget(self._image_size_label)
        
        # ROI area info
        self._roi_area_label = QLabel("ROI 면적: 0.0% of image")
        self._roi_area_label.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        layout.addWidget(self._roi_area_label)
        
        # Control buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)
        
        # Clear ROI button
        self._clear_button = QPushButton("ROI 초기화")
        self._clear_button.clicked.connect(self._on_clear_roi)
        button_layout.addWidget(self._clear_button)
        
        # Full image button
        self._full_image_button = QPushButton("전체 이미지 선택")
        self._full_image_button.clicked.connect(self._on_select_full_image)
        button_layout.addWidget(self._full_image_button)
        
        layout.addLayout(button_layout)
        
        # Add stretch
        layout.addStretch()
        
    def _on_coordinate_changed(self) -> None:
        """Handle coordinate input changes."""
        # Only emit signal if we have valid image dimensions
        if self._image_width > 0 and self._image_height > 0:
            roi = self.get_roi_from_fields()
            self._update_roi_area_display(roi)
            self.roi_updated.emit(roi)
            
    def _on_clear_roi(self) -> None:
        """Handle clear ROI button click."""
        self.update_from_roi(None)
        self.roi_updated.emit(None)
        
    def _on_select_full_image(self) -> None:
        """Handle select full image button click."""
        if self._image_width > 0 and self._image_height > 0:
            full_roi = ROIConfig(0, 0, self._image_width, self._image_height)
            self.update_from_roi(full_roi)
            self.roi_updated.emit(full_roi)
            
    def update_from_roi(self, roi: ROIConfig | None) -> None:
        """
        Update spinboxes from ROI configuration without triggering signals.
        
        Args:
            roi: ROI configuration or None to clear
        """
        # Block signals to prevent infinite loop
        for spinbox in [self._x_spinbox, self._y_spinbox, self._width_spinbox, self._height_spinbox]:
            spinbox.blockSignals(True)
            
        try:
            if roi is None:
                self._x_spinbox.setValue(0)
                self._y_spinbox.setValue(0)
                self._width_spinbox.setValue(0)
                self._height_spinbox.setValue(0)
            else:
                self._x_spinbox.setValue(roi.x)
                self._y_spinbox.setValue(roi.y)
                self._width_spinbox.setValue(roi.width)
                self._height_spinbox.setValue(roi.height)
                
            self._update_roi_area_display(roi)
            
        finally:
            # Restore signals
            for spinbox in [self._x_spinbox, self._y_spinbox, self._width_spinbox, self._height_spinbox]:
                spinbox.blockSignals(False)
                
    def update_image_size(self, width: int, height: int) -> None:
        """
        Update image size information.
        
        Args:
            width: Image width
            height: Image height
        """
        self._image_width = width
        self._image_height = height
        self._image_size_label.setText(f"이미지 크기: {width} × {height}")
        
        # Update spinbox ranges
        self._x_spinbox.setRange(0, max(0, width - 1))
        self._y_spinbox.setRange(0, max(0, height - 1))
        self._width_spinbox.setRange(0, width)
        self._height_spinbox.setRange(0, height)
        
        # Update ROI area display
        current_roi = self.get_roi_from_fields()
        self._update_roi_area_display(current_roi)
        
    def get_roi_from_fields(self) -> ROIConfig:
        """
        Get ROI configuration from current spinbox values.
        
        Returns:
            ROIConfig based on current input fields
        """
        return ROIConfig(
            x=self._x_spinbox.value(),
            y=self._y_spinbox.value(),
            width=self._width_spinbox.value(),
            height=self._height_spinbox.value()
        )
        
    def _update_roi_area_display(self, roi: ROIConfig | None) -> None:
        """
        Update ROI area percentage display.
        
        Args:
            roi: ROI configuration or None
        """
        if roi is None or self._image_width == 0 or self._image_height == 0:
            self._roi_area_label.setText("ROI 면적: 0.0% of image")
            self._roi_area_label.setStyleSheet("color: #9E9E9E; font-size: 11px;")
            return
            
        # Calculate area ratio
        roi_area = roi.width * roi.height
        image_area = self._image_width * self._image_height
        
        if image_area > 0:
            ratio = roi_area / image_area
            ratio_percent = ratio * 100
            
            # Color based on minimum area threshold
            if ratio >= MIN_ROI_AREA_RATIO:
                color = "#43A047"  # Green - good
            else:
                color = "#FB8C00"  # Amber - warning
                
            self._roi_area_label.setText(f"ROI 면적: {ratio_percent:.1f}% of image")
            self._roi_area_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 500;")
        else:
            self._roi_area_label.setText("ROI 면적: 0.0% of image")
            self._roi_area_label.setStyleSheet("color: #9E9E9E; font-size: 11px;")
            
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable all controls.
        
        Args:
            enabled: Whether to enable controls
        """
        for widget in [
            self._x_spinbox, self._y_spinbox, self._width_spinbox, self._height_spinbox,
            self._clear_button, self._full_image_button
        ]:
            widget.setEnabled(enabled)