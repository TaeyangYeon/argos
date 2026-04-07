"""
Drop zone component for file upload with drag & drop support.

This module provides a styled drop zone widget for uploading images
with visual feedback for different states and validation.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QWidget
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import QFont, QDragEnterEvent, QDragLeaveEvent, QDropEvent

from core.image_store import ImageType
from config.constants import SUPPORTED_FORMATS


class DropZone(QFrame):
    """
    Drag & drop file upload zone with visual state feedback.
    
    Features:
    - Visual states: default, hover, drag_over, error
    - Drag & drop support for image files
    - Click to open file dialog
    - Count badge for uploaded files
    - Error state with auto-reset
    """
    
    # Signal emitted when files are dropped or selected
    files_dropped = pyqtSignal(list)  # list of file path strings
    
    def __init__(
        self, 
        image_type: ImageType, 
        label: str, 
        accent_color: str, 
        parent=None
    ):
        """
        Initialize the drop zone.
        
        Args:
            image_type: Type of images this zone accepts
            label: Display label (e.g., "Align OK")
            accent_color: Accent color for borders and highlights
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._image_type = image_type
        self._label = label
        self._accent_color = accent_color
        self._count = 0
        self._state = "default"  # default, hover, drag_over, error
        
        self._setup_ui()
        self._setup_drag_drop()
        self._apply_styling()
        
    def _setup_ui(self) -> None:
        """Setup the drop zone UI layout."""
        # Set minimum size
        self.setMinimumSize(200, 180)
        
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Upload icon
        self._icon_label = QLabel("⬆")
        icon_font = QFont()
        icon_font.setPointSize(32)
        self._icon_label.setFont(icon_font)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(f"color: {self._accent_color};")
        layout.addWidget(self._icon_label)
        
        # Label text
        self._label_widget = QLabel(self._label)
        label_font = QFont()
        label_font.setPointSize(14)
        label_font.setBold(True)
        self._label_widget.setFont(label_font)
        self._label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_widget.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(self._label_widget)
        
        # Hint text
        self._hint_label = QLabel("이미지를 드래그하거나\n클릭하여 업로드")
        hint_font = QFont()
        hint_font.setPointSize(12)
        self._hint_label.setFont(hint_font)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(self._hint_label)
        
        # Count badge
        self._count_badge = QLabel("0장")
        badge_font = QFont()
        badge_font.setPointSize(11)
        badge_font.setBold(True)
        self._count_badge.setFont(badge_font)
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.setMinimumHeight(24)
        self._count_badge.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: #9E9E9E;
                border-radius: 12px;
                padding: 4px 8px;
            }}
        """)
        layout.addWidget(self._count_badge)
        
    def _setup_drag_drop(self) -> None:
        """Setup drag and drop functionality."""
        self.setAcceptDrops(True)
        
        # Make widget clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def _apply_styling(self) -> None:
        """Apply styling based on current state."""
        if self._state == "default":
            border_style = "dashed"
            border_color = self._accent_color
            border_opacity = "99"  # 60% opacity approximated
            bg_opacity = "14"      # 8% opacity approximated
            
        elif self._state == "hover":
            border_style = "solid"
            border_color = self._accent_color
            border_opacity = "FF"  # 100% opacity
            bg_opacity = "28"      # Higher opacity for hover
            
        elif self._state == "drag_over":
            border_style = "solid"
            border_color = self._accent_color
            border_opacity = "FF"  # 100% opacity
            bg_opacity = "33"      # 20% opacity
            # Scale icon
            icon_font = QFont()
            icon_font.setPointSize(40)
            self._icon_label.setFont(icon_font)
            
        elif self._state == "error":
            border_style = "solid"
            border_color = "#E53935"
            border_opacity = "FF"
            bg_opacity = "14"      # 8% opacity
            
        else:
            border_style = "dashed"
            border_color = self._accent_color
            border_opacity = "99"
            bg_opacity = "14"
        
        # Convert hex color to rgba for opacity
        hex_color = border_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            bg_alpha = int(bg_opacity, 16) / 255.0
            
            self.setStyleSheet(f"""
                DropZone {{
                    border: 2px {border_style} {border_color};
                    border-radius: 12px;
                    background-color: rgba({r}, {g}, {b}, {bg_alpha});
                }}
            """)
            
    def _reset_state(self) -> None:
        """Reset to default state."""
        self._state = "default"
        # Reset icon size
        icon_font = QFont()
        icon_font.setPointSize(32)
        self._icon_label.setFont(icon_font)
        self._apply_styling()
        
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            # Check if any of the URLs are valid image files
            valid_files = []
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() in SUPPORTED_FORMATS:
                    valid_files.append(file_path)
                    
            if valid_files:
                event.acceptProposedAction()
                self._state = "drag_over"
                self._apply_styling()
                return
                
        event.ignore()
        
    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave events."""
        self._reset_state()
        
    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events."""
        file_paths = []
        
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path and Path(file_path).suffix.lower() in SUPPORTED_FORMATS:
                file_paths.append(file_path)
                
        if file_paths:
            self.files_dropped.emit(file_paths)
            
        self._reset_state()
        event.acceptProposedAction()
        
    def enterEvent(self, event) -> None:
        """Handle mouse enter events."""
        if self._state == "default":
            self._state = "hover"
            self._apply_styling()
        super().enterEvent(event)
        
    def leaveEvent(self, event) -> None:
        """Handle mouse leave events."""
        if self._state == "hover":
            self._reset_state()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event) -> None:
        """Handle mouse click to open file dialog."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()
        super().mousePressEvent(event)
        
    def _open_file_dialog(self) -> None:
        """Open file dialog for multiple file selection."""
        # Create filter string for supported formats
        filter_formats = []
        for fmt in SUPPORTED_FORMATS:
            filter_formats.append(f"*{fmt}")
        filter_string = f"Images ({' '.join(filter_formats)})"
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            f"Select {self._label} Images",
            "",
            filter_string
        )
        
        if file_paths:
            self.files_dropped.emit(file_paths)
            
    def update_count(self, count: int) -> None:
        """
        Update the count badge display.
        
        Args:
            count: Number of uploaded files
        """
        self._count = count
        self._count_badge.setText(f"{count}장")
        
        if count > 0:
            # Badge with accent color background
            hex_color = self._accent_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                
                self._count_badge.setStyleSheet(f"""
                    QLabel {{
                        background: {self._accent_color};
                        color: #FFFFFF;
                        border-radius: 12px;
                        padding: 4px 8px;
                    }}
                """)
        else:
            # Transparent background for zero count
            self._count_badge.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    color: #9E9E9E;
                    border-radius: 12px;
                    padding: 4px 8px;
                }}
            """)
            
    def set_error_state(self, message: str) -> None:
        """
        Briefly flash error state then revert to default.
        
        Args:
            message: Error message (currently not displayed)
        """
        self._state = "error"
        self._apply_styling()
        
        # Reset to default state after 1500ms
        QTimer.singleShot(1500, self._reset_state)
        
    def get_image_type(self) -> ImageType:
        """Get the image type this drop zone handles."""
        return self._image_type