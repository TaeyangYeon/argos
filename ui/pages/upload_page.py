"""
Image upload page for the Argos vision algorithm design application.

This module provides the image upload interface for managing
training and test images.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QWidget, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .base_page import BasePage, PageHeader
from ui.components.sidebar import PageID
from ui.components.drop_zone import DropZone
from ui.components.toast import ToastMessage
from ui.components.thumbnail_grid import ThumbnailGrid
from ui.components.image_viewer_dialog import ImageViewerDialog
from core.image_store import ImageStore, ImageType
from core.validators import ImageValidator
from core.exceptions import InputValidationError


class UploadPage(BasePage):
    """
    Image upload page for managing project images.
    
    Features:
    - Three drop zones for different image types (Align OK, Inspection OK/NG)
    - Drag & drop and click-to-upload functionality
    - Real-time validation with error feedback
    - NG warning banner when insufficient NG samples
    - Upload summary and clear all functionality
    """
    
    # Signal emitted when images are updated
    images_updated = pyqtSignal()
    
    def __init__(self, image_store: ImageStore, parent=None):
        """
        Initialize the upload page.
        
        Args:
            image_store: ImageStore instance for data management
            parent: Parent widget
        """
        self._image_store = image_store
        
        # Initialize UI components as None
        self._align_ok_zone = None
        self._inspection_ok_zone = None
        self._inspection_ng_zone = None
        self._ng_warning_banner = None
        self._summary_labels = {}
        self._toast = None
        self._thumbnail_grid = None
        self._filter_buttons = {}
        self._current_filter = None
        
        super().__init__(PageID.UPLOAD, "이미지 업로드", parent)
        
    def setup_ui(self) -> None:
        """Setup the upload page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page header
        header = PageHeader("이미지 업로드", "분석에 사용할 이미지를 업로드하세요.")
        layout.addWidget(header)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(16)
        
        # NG warning banner (initially hidden)
        self._setup_ng_warning_banner(content_layout)
        
        # Drop zones row
        self._setup_drop_zones(content_layout)
        
        # Thumbnail grid section
        self._setup_thumbnail_section(content_layout)
        
        # Upload summary
        self._setup_summary_section(content_layout)
        
        # Clear all button
        self._setup_clear_button(content_layout)
        
        # Add stretch to push content to top
        content_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Set content widget to scroll area and add to main layout
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Create toast message overlay
        self._toast = ToastMessage(self)
        
        # Initial UI refresh
        self._refresh_ui()
        
    def _setup_ng_warning_banner(self, parent_layout: QVBoxLayout) -> None:
        """Setup the NG warning banner."""
        self._ng_warning_banner = QFrame()
        self._ng_warning_banner.setVisible(False)  # Initially hidden
        
        banner_layout = QHBoxLayout(self._ng_warning_banner)
        banner_layout.setContentsMargins(16, 12, 16, 12)
        banner_layout.setSpacing(8)
        
        # Warning text
        warning_text = QLabel()
        warning_font = QFont()
        warning_font.setPointSize(12)
        warning_text.setFont(warning_font)
        warning_text.setWordWrap(True)
        banner_layout.addWidget(warning_text)
        
        self._warning_text_label = warning_text
        
        # Style the banner
        self._ng_warning_banner.setStyleSheet("""
            QFrame {
                background-color: rgba(251, 140, 0, 0.15);
                border-left: 4px solid #FB8C00;
                border-radius: 6px;
            }
            QLabel {
                color: #FB8C00;
            }
        """)
        
        parent_layout.addWidget(self._ng_warning_banner)
        
    def _setup_drop_zones(self, parent_layout: QVBoxLayout) -> None:
        """Setup the three drop zones."""
        # Drop zones container
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(16)
        
        # Create drop zones with specified colors
        self._align_ok_zone = DropZone(ImageType.ALIGN_OK, "Align OK", "#1E88E5")
        self._inspection_ok_zone = DropZone(ImageType.INSPECTION_OK, "Inspection OK", "#43A047")
        self._inspection_ng_zone = DropZone(ImageType.INSPECTION_NG, "Inspection NG", "#E53935")
        
        # Connect signals
        self._align_ok_zone.files_dropped.connect(
            lambda files: self._handle_files_dropped(files, ImageType.ALIGN_OK)
        )
        self._inspection_ok_zone.files_dropped.connect(
            lambda files: self._handle_files_dropped(files, ImageType.INSPECTION_OK)
        )
        self._inspection_ng_zone.files_dropped.connect(
            lambda files: self._handle_files_dropped(files, ImageType.INSPECTION_NG)
        )
        
        # Add zones to layout with equal stretch
        zones_layout.addWidget(self._align_ok_zone, 1)
        zones_layout.addWidget(self._inspection_ok_zone, 1)
        zones_layout.addWidget(self._inspection_ng_zone, 1)
        
        parent_layout.addLayout(zones_layout)
        
    def _setup_summary_section(self, parent_layout: QVBoxLayout) -> None:
        """Setup the upload summary section."""
        # Summary card
        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_card.setFixedHeight(100)
        
        card_layout = QVBoxLayout(summary_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(8)
        
        # Title
        title_label = QLabel("업로드 현황 요약")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E0E0E0;")
        card_layout.addWidget(title_label)
        
        # Summary stats in two rows
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(4)
        
        # First row: Align OK and Inspection OK
        row1_layout = QHBoxLayout()
        
        self._summary_labels["align_ok"] = QLabel("Align OK: 0장")
        self._summary_labels["align_ok"].setStyleSheet("color: #1E88E5; font-weight: 500;")
        row1_layout.addWidget(self._summary_labels["align_ok"])
        
        row1_layout.addWidget(QLabel("  │  "))  # Separator
        
        self._summary_labels["inspection_ok"] = QLabel("Inspection OK: 0장")
        self._summary_labels["inspection_ok"].setStyleSheet("color: #43A047; font-weight: 500;")
        row1_layout.addWidget(self._summary_labels["inspection_ok"])
        
        row1_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        stats_layout.addLayout(row1_layout)
        
        # Second row: Inspection NG and Total
        row2_layout = QHBoxLayout()
        
        self._summary_labels["inspection_ng"] = QLabel("Inspection NG: 0장")
        self._summary_labels["inspection_ng"].setStyleSheet("color: #E53935; font-weight: 500;")
        row2_layout.addWidget(self._summary_labels["inspection_ng"])
        
        row2_layout.addWidget(QLabel("  │  "))  # Separator
        
        self._summary_labels["total"] = QLabel("전체: 0장")
        self._summary_labels["total"].setStyleSheet("color: #FB8C00; font-weight: 500;")
        row2_layout.addWidget(self._summary_labels["total"])
        
        row2_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        stats_layout.addLayout(row2_layout)
        
        card_layout.addLayout(stats_layout)
        parent_layout.addWidget(summary_card)
        
    def _setup_clear_button(self, parent_layout: QVBoxLayout) -> None:
        """Setup the clear all button."""
        button_layout = QHBoxLayout()
        
        # Spacer to right-align the button
        button_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Clear button
        self._clear_button = QPushButton("🗑 전체 초기화")
        self._clear_button.setObjectName("dangerBtn")
        self._clear_button.clicked.connect(self._handle_clear_all)
        button_layout.addWidget(self._clear_button)
        
        parent_layout.addLayout(button_layout)
        
    def _setup_thumbnail_section(self, parent_layout: QVBoxLayout) -> None:
        """Setup the thumbnail grid section with filter tabs."""
        # Section header with filter tabs
        header_layout = QHBoxLayout()
        
        # Section title
        title_label = QLabel("업로드된 이미지")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E0E0E0;")
        header_layout.addWidget(title_label)
        
        # Add some spacing
        header_layout.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Filter tabs
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filters = [
            ("전체", None),
            ("Align OK", ImageType.ALIGN_OK),
            ("Inspection OK", ImageType.INSPECTION_OK),
            ("Inspection NG", ImageType.INSPECTION_NG)
        ]
        
        for filter_name, filter_type in filters:
            button = QPushButton(filter_name)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, ft=filter_type: self._on_filter_changed(ft))
            
            if filter_type is None:  # "전체" button starts selected
                button.setChecked(True)
                button.setObjectName("primaryBtn")
            
            self._filter_buttons[filter_type] = button
            filter_layout.addWidget(button)
            
        header_layout.addLayout(filter_layout)
        parent_layout.addLayout(header_layout)
        
        # Thumbnail grid
        self._thumbnail_grid = ThumbnailGrid()
        self._thumbnail_grid.setMinimumHeight(200)
        self._thumbnail_grid.setMaximumHeight(400)
        
        # Connect grid signals
        self._thumbnail_grid.view_requested.connect(self._on_view_requested)
        self._thumbnail_grid.delete_requested.connect(self._on_delete_requested)
        
        parent_layout.addWidget(self._thumbnail_grid)
        
    def _on_filter_changed(self, filter_type: ImageType | None) -> None:
        """
        Handle filter tab selection change.
        
        Args:
            filter_type: Selected image type filter, or None for all
        """
        self._current_filter = filter_type
        
        # Update button states (exclusive selection)
        for ft, button in self._filter_buttons.items():
            if ft == filter_type:
                button.setChecked(True)
                button.setObjectName("primaryBtn")
            else:
                button.setChecked(False)
                button.setObjectName("")
            # Force style update
            button.setStyle(button.style())
            
        # Refresh grid with new filter
        self._refresh_grid()
        
    def _on_view_requested(self, image_id: str) -> None:
        """
        Handle view request from thumbnail grid.
        
        Args:
            image_id: ID of image to view
        """
        # Get image metadata
        image_meta = self._image_store.get(image_id)
        if image_meta:
            # Open image viewer dialog
            dialog = ImageViewerDialog(image_meta, self._image_store, self)
            dialog.exec()
            
    def _on_delete_requested(self, image_id: str) -> None:
        """
        Handle delete request from thumbnail grid.
        
        Args:
            image_id: ID of image to delete
        """
        # Show confirmation dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("이미지 삭제")
        msg_box.setText("이 이미지를 삭제하시겠습니까?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            # Remove from store
            self._image_store.remove(image_id)
            
            # Refresh UI
            self._refresh_ui()
            
            # Show success toast
            self._toast.show_success("이미지 삭제 완료")
            
            # Emit update signal
            self.images_updated.emit()
            
    def _refresh_grid(self) -> None:
        """Refresh the thumbnail grid with current filter."""
        if not self._thumbnail_grid:
            return
            
        # Get all images from store
        all_images = self._image_store.get_all()
        
        # Filter images based on current filter
        if self._current_filter is None:
            # Show all images
            filtered_images = all_images
        else:
            # Filter by type
            filtered_images = [
                img for img in all_images 
                if img.image_type == self._current_filter
            ]
            
        # Update grid
        self._thumbnail_grid.refresh(filtered_images)
        
    def _handle_files_dropped(self, file_paths: list, image_type: ImageType) -> None:
        """
        Handle files dropped on a drop zone.
        
        Args:
            file_paths: List of dropped file paths
            image_type: Type of images being uploaded
        """
        success_count = 0
        error_count = 0
        
        # Get the appropriate drop zone for error display
        drop_zone = {
            ImageType.ALIGN_OK: self._align_ok_zone,
            ImageType.INSPECTION_OK: self._inspection_ok_zone,
            ImageType.INSPECTION_NG: self._inspection_ng_zone
        }[image_type]
        
        for file_path in file_paths:
            try:
                # Validate image
                ImageValidator.validate_image(file_path)
                
                # Add to store
                self._image_store.add(file_path, image_type)
                
                # Show success toast
                filename = Path(file_path).name
                self._toast.show_success(f"{filename} 업로드 완료")
                success_count += 1
                
            except InputValidationError as e:
                # Show error on drop zone and toast
                drop_zone.set_error_state(str(e))
                self._toast.show_error(str(e))
                error_count += 1
                
        # Refresh UI to update counts and warning banner
        self._refresh_ui()
        
        # Emit update signal
        self.images_updated.emit()
        
    def _handle_clear_all(self) -> None:
        """Handle clear all button click with confirmation."""
        # Show confirmation dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("전체 초기화")
        msg_box.setText("업로드된 모든 이미지가 삭제됩니다. 계속하시겠습니까?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            # Clear all images
            self._image_store.clear()
            
            # Refresh UI
            self._refresh_ui()
            
            # Show success toast
            self._toast.show_success("전체 초기화 완료")
            
            # Emit update signal
            self.images_updated.emit()
            
    def _refresh_ui(self) -> None:
        """
        Update all UI components with current data.
        
        Updates drop zone counts, summary labels, and NG warning banner visibility.
        """
        # Get current counts
        align_ok_count = self._image_store.count(ImageType.ALIGN_OK)
        inspection_ok_count = self._image_store.count(ImageType.INSPECTION_OK)
        inspection_ng_count = self._image_store.count(ImageType.INSPECTION_NG)
        total_count = self._image_store.count()
        
        # Update drop zone count badges
        if self._align_ok_zone:
            self._align_ok_zone.update_count(align_ok_count)
        if self._inspection_ok_zone:
            self._inspection_ok_zone.update_count(inspection_ok_count)
        if self._inspection_ng_zone:
            self._inspection_ng_zone.update_count(inspection_ng_count)
            
        # Update summary labels
        if self._summary_labels:
            self._summary_labels["align_ok"].setText(f"Align OK: {align_ok_count}장")
            self._summary_labels["inspection_ok"].setText(f"Inspection OK: {inspection_ok_count}장")
            self._summary_labels["inspection_ng"].setText(f"Inspection NG: {inspection_ng_count}장")
            self._summary_labels["total"].setText(f"전체: {total_count}장")
            
        # Update NG warning banner visibility
        self._update_ng_warning(inspection_ok_count, inspection_ng_count)
        
        # Update thumbnail grid
        self._refresh_grid()
        
    def _update_ng_warning(self, ok_count: int, ng_count: int) -> None:
        """
        Update NG warning banner visibility.
        
        Args:
            ok_count: Number of OK images
            ng_count: Number of NG images
        """
        # Show banner when OK images exist but no NG images
        should_show = (ok_count > 0) and (ng_count == 0)
        
        if should_show:
            warning_text = (
                "⚠️  NG 이미지가 필요합니다.\n"
                "Inspection 알고리즘 설계를 위해 NG 이미지를 1장 이상 업로드해주세요.\n"
                f"현재 등록: OK {ok_count}장 / NG 0장"
            )
            self._warning_text_label.setText(warning_text)
            self._ng_warning_banner.setVisible(True)
        else:
            self._ng_warning_banner.setVisible(False)
            
    def showEvent(self, event) -> None:
        """Override showEvent to refresh data when page becomes visible."""
        super().showEvent(event)
        self._refresh_ui()