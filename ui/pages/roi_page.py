"""
ROI (Region of Interest) configuration page for the Argos vision algorithm design application.

This module provides the interface for defining and adjusting
regions of interest for vision analysis using mouse interaction and coordinate input.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QStackedWidget, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import numpy as np

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID
from ui.components.roi_canvas import ROICanvas
from ui.components.roi_controls import ROIControls
from ui.components.toast import ToastMessage
from core.image_store import ImageStore, ImageType, ImageMeta
from core.models import ROIConfig
from core.validators import ROIValidator
from core.exceptions import InputValidationError


class ROIPage(BasePage):
    """
    ROI configuration page for defining analysis regions.
    
    Features:
    - Interactive canvas with mouse drag ROI selection
    - Coordinate input controls with validation
    - Image selector for choosing reference image
    - Real-time ROI validation and feedback
    - Empty state handling for no images
    """
    
    # Signals
    roi_confirmed = pyqtSignal(object)    # ROIConfig
    navigate_requested = pyqtSignal(str)  # PageID value
    
    def __init__(self, image_store: ImageStore, parent=None):
        """
        Initialize the ROI page.
        
        Args:
            image_store: ImageStore instance for accessing images
            parent: Parent widget
        """
        self._image_store = image_store
        self._confirmed_roi = None
        self._selected_image_meta = None
        
        super().__init__(PageID.ROI, "ROI 설정", parent)
        
        # Create toast overlay
        self._toast = ToastMessage(self)
        
    def setup_ui(self) -> None:
        """Setup the ROI page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("ROI 설정", "검사 영역을 마우스로 드래그하여 지정하세요.")
        layout.addWidget(header)
        
        # Main content area with stacked widget for empty state
        self._content_stack = QStackedWidget()
        
        # Main ROI interface
        self._main_widget = self._create_main_interface()
        self._content_stack.addWidget(self._main_widget)
        
        # Empty state widget
        self._empty_widget = self._create_empty_state()
        self._content_stack.addWidget(self._empty_widget)
        
        layout.addWidget(self._content_stack)
        
    def _create_main_interface(self) -> QWidget:
        """Create the main ROI interface widget."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Left: ROI Canvas (expanding)
        self._roi_canvas = ROICanvas()
        self._roi_canvas.roi_changed.connect(self._on_canvas_roi_changed)
        layout.addWidget(self._roi_canvas, 1)  # Give it stretch
        
        # Right: Controls panel
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setSpacing(16)
        
        # Image selector
        selector_widget = self._create_image_selector()
        right_panel_layout.addWidget(selector_widget)
        
        # ROI controls
        self._roi_controls = ROIControls()
        self._roi_controls.roi_updated.connect(self._on_controls_roi_updated)
        right_panel_layout.addWidget(self._roi_controls)
        
        # Confirm ROI button
        self._confirm_button = QPushButton("✅ ROI 확정")
        self._confirm_button.setObjectName("primaryBtn")
        self._confirm_button.clicked.connect(self._on_confirm_roi)
        self._confirm_button.setMinimumHeight(40)
        right_panel_layout.addWidget(self._confirm_button)
        
        # Add stretch to push everything to top
        right_panel_layout.addStretch()
        
        layout.addLayout(right_panel_layout)
        
        return widget
        
    def _create_image_selector(self) -> QWidget:
        """Create the image selector widget."""
        widget = QWidget()
        widget.setFixedWidth(220)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("이미지 선택")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(title_label)
        
        # Combobox
        self._image_selector = QComboBox()
        self._image_selector.currentIndexChanged.connect(self._on_image_selected)
        layout.addWidget(self._image_selector)
        
        # Style the widget
        widget.setStyleSheet("""
            QWidget {
                background-color: #16213E;
                border: 1px solid #2A2A4A;
                border-radius: 8px;
            }
        """)
        
        return widget
        
    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon and message
        message_label = QLabel("📁 먼저 이미지를 업로드해주세요.")
        message_font = QFont()
        message_font.setPointSize(18)
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("color: #9E9E9E; padding: 20px;")
        layout.addWidget(message_label)
        
        # Navigation button
        nav_button = QPushButton("이미지 업로드로 이동")
        nav_button.setObjectName("primaryBtn")
        nav_button.clicked.connect(lambda: self.navigate_requested.emit(PageID.UPLOAD.value))
        nav_button.setMinimumHeight(40)
        layout.addWidget(nav_button)
        
        return widget
        
    def _on_image_selected(self, index: int) -> None:
        """Handle image selection change."""
        if index < 0:
            return
            
        image_id = self._image_selector.itemData(index)
        if image_id:
            # Load selected image
            self._selected_image_meta = self._image_store.get(image_id)
            if self._selected_image_meta:
                # Load image into canvas
                image_array = self._image_store.load_image(image_id)
                if image_array is not None:
                    self._roi_canvas.load_image(image_array)
                    
                    # Update controls with image dimensions
                    self._roi_controls.update_image_size(
                        self._selected_image_meta.width,
                        self._selected_image_meta.height
                    )
                    
                    # Enable controls
                    self._roi_controls.set_enabled(True)
                    self._confirm_button.setEnabled(True)
                else:
                    self._toast.show_error("이미지를 불러올 수 없습니다.")
                    
    def _on_canvas_roi_changed(self, roi: ROIConfig | None) -> None:
        """Handle ROI change from canvas."""
        # Update controls without triggering their signals
        self._roi_controls.update_from_roi(roi)
        
    def _on_controls_roi_updated(self, roi: ROIConfig | None) -> None:
        """Handle ROI update from controls."""
        # Update canvas
        if roi is None:
            self._roi_canvas.clear_roi()
        else:
            self._roi_canvas.set_roi(roi)
            
    def _on_confirm_roi(self) -> None:
        """Handle ROI confirmation button click."""
        current_roi = self._roi_canvas.get_roi()
        
        if current_roi is None:
            self._toast.show_error("ROI를 먼저 선택해주세요.")
            return
            
        if self._selected_image_meta is None:
            self._toast.show_error("이미지를 먼저 선택해주세요.")
            return
            
        try:
            # Load image for validation
            image_array = self._image_store.load_image(self._selected_image_meta.id)
            if image_array is None:
                self._toast.show_error("이미지를 불러올 수 없습니다.")
                return
                
            # Validate ROI
            ROIValidator.validate_roi(current_roi, image_array)
            
            # Save confirmed ROI
            self._confirmed_roi = current_roi
            
            # Calculate area ratio for display
            roi_area = current_roi.width * current_roi.height
            image_area = self._selected_image_meta.width * self._selected_image_meta.height
            roi_ratio = (roi_area / image_area) * 100 if image_area > 0 else 0
            
            # Show success message
            self._toast.show_success(
                f"ROI 확정: {current_roi.width}×{current_roi.height} "
                f"({roi_ratio:.1f}% of image)"
            )
            
            # Emit confirmation signal
            self.roi_confirmed.emit(self._confirmed_roi)
            
        except InputValidationError as e:
            self._toast.show_error(str(e))
            
    def refresh_image_list(self) -> None:
        """Refresh the image selector list from image store."""
        self._image_selector.clear()
        
        images = self._image_store.get_all()
        
        if not images:
            # Show empty state
            self._content_stack.setCurrentWidget(self._empty_widget)
            return
        else:
            # Show main interface
            self._content_stack.setCurrentWidget(self._main_widget)
            
        # Populate image selector
        for image_meta in images:
            filename = Path(image_meta.file_path).name
            type_prefix = {
                ImageType.ALIGN_OK: "[Align OK]",
                ImageType.INSPECTION_OK: "[Insp. OK]",
                ImageType.INSPECTION_NG: "[Insp. NG]"
            }.get(image_meta.image_type, "[Unknown]")
            
            display_name = f"{type_prefix} {filename}"
            self._image_selector.addItem(display_name, image_meta.id)
            
        # If we had a previously selected image, try to restore it
        if self._selected_image_meta:
            for i in range(self._image_selector.count()):
                if self._image_selector.itemData(i) == self._selected_image_meta.id:
                    self._image_selector.setCurrentIndex(i)
                    break
                    
        # If no selection yet, select first item
        if self._image_selector.currentIndex() == -1 and self._image_selector.count() > 0:
            self._image_selector.setCurrentIndex(0)
            
    def get_confirmed_roi(self) -> ROIConfig | None:
        """
        Get the confirmed ROI configuration.
        
        Returns:
            Confirmed ROIConfig or None if not confirmed
        """
        return self._confirmed_roi
        
    def get_selected_image_meta(self) -> ImageMeta | None:
        """
        Get the currently selected image metadata.
        
        Returns:
            Selected ImageMeta or None
        """
        return self._selected_image_meta
        
    def showEvent(self, event) -> None:
        """Override showEvent to refresh data when page becomes visible."""
        super().showEvent(event)
        self.refresh_image_list()