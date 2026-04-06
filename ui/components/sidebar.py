"""
Sidebar navigation component for the Argos vision algorithm design application.

This module provides a collapsible sidebar with navigation menu items,
progress tracking, and smooth animations.
"""

from enum import Enum
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QPushButton, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import pyqtSignal, QPropertyAnimation, QEasingCurve, Qt
from PyQt6.QtGui import QFont

from core.logger import get_logger


class PageID(Enum):
    """Enumeration of page identifiers for navigation."""
    DASHBOARD = "dashboard"
    UPLOAD = "upload"
    ROI = "roi"
    ANALYSIS = "analysis"
    RESULTS = "results"
    SETTINGS = "settings"


class SidebarMenuItem(QWidget):
    """
    Individual menu item in the sidebar navigation.
    
    Provides visual feedback for active/inactive states and emits
    signals when clicked.
    """
    
    # Signal emitted when menu item is clicked
    clicked = pyqtSignal(PageID)
    
    def __init__(self, page_id: PageID, icon: str, label: str, parent=None):
        """
        Initialize the sidebar menu item.
        
        Args:
            page_id: Unique page identifier
            icon: Unicode emoji or text symbol
            label: Korean display name
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.page_id = page_id
        self._is_active = False
        self._logger = get_logger("sidebar")
        
        self._setup_ui(icon, label)
        self._connect_signals()
        
    def _setup_ui(self, icon: str, label: str) -> None:
        """Setup the menu item UI."""
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Icon label
        self._icon_label = QLabel(icon)
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)
        
        # Text label
        self._text_label = QLabel(label)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._text_label)
        
        # Spacer
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Active indicator arrow (hidden initially)
        self._indicator = QLabel("→")
        self._indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._indicator.setVisible(False)
        layout.addWidget(self._indicator)
        
        # Set initial inactive state (don't call set_active here to avoid interference)
        self._is_active = False
        
    def _connect_signals(self) -> None:
        """Connect signals."""
        # No direct signals needed - using mousePressEvent instead
        pass
        
    def mousePressEvent(self, event) -> None:
        """Handle mouse click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_id)
            self._logger.debug(f"Menu item clicked: {self.page_id.value}")
        super().mousePressEvent(event)
        
    def set_active(self, active: bool) -> None:
        """
        Set the active state of the menu item.
        
        Args:
            active: True if this item should be highlighted as active
        """
        self._is_active = active
        
        if active:
            # Active state: accent background, white text, border
            self.setStyleSheet("""
                SidebarMenuItem {
                    background-color: #1E88E5;
                    border-left: 3px solid #FFFFFF;
                    border-radius: 6px;
                }
                QLabel {
                    color: #FFFFFF;
                    background: transparent;
                }
            """)
            # Explicitly show indicator after applying stylesheet
            self._indicator.setVisible(True)
            self._indicator.show()
        else:
            # Inactive state: transparent background, muted text
            self.setStyleSheet("""
                SidebarMenuItem {
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                }
                SidebarMenuItem:hover {
                    background-color: rgba(30, 136, 229, 0.1);
                }
                QLabel {
                    color: #9E9E9E;
                    background: transparent;
                }
            """)
            # Explicitly hide indicator  
            self._indicator.setVisible(False)
            self._indicator.hide()
            
    def is_active(self) -> bool:
        """Return whether this menu item is currently active."""
        return self._is_active


class ArgosSidebar(QFrame):
    """
    Main sidebar navigation component with collapsible functionality.
    
    Provides navigation between different application pages with
    smooth animations and progress tracking.
    """
    
    # Signal emitted when page navigation is requested
    page_changed = pyqtSignal(PageID)
    
    def __init__(self, parent=None):
        """Initialize the sidebar."""
        super().__init__(parent)
        
        self._logger = get_logger("sidebar")
        self._is_collapsed = False
        self._menu_items = {}
        self._current_page = PageID.DASHBOARD
        
        self._setup_ui()
        self._setup_animation()
        self._connect_signals()
        
        # Set initial state
        self.navigate_to(PageID.DASHBOARD)
        
    def _setup_ui(self) -> None:
        """Setup the sidebar UI."""
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setMaximumWidth(220)
        
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)
        
        # Collapse button at the top
        self._collapse_button = QPushButton("◀")
        self._collapse_button.setFixedSize(32, 32)
        self._collapse_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #9E9E9E;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        
        # Center the collapse button
        collapse_layout = QHBoxLayout()
        collapse_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        collapse_layout.addWidget(self._collapse_button)
        collapse_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        collapse_widget = QWidget()
        collapse_widget.setLayout(collapse_layout)
        layout.addWidget(collapse_widget)
        
        # Menu items
        menu_items_data = [
            (PageID.DASHBOARD, "📊", "대시보드"),
            (PageID.UPLOAD, "📁", "이미지 업로드"),
            (PageID.ROI, "✂️", "ROI 설정"),
            (PageID.ANALYSIS, "▶️", "분석 실행"),
            (PageID.RESULTS, "📋", "결과 보기"),
            (PageID.SETTINGS, "⚙️", "설정"),
        ]
        
        for page_id, icon, label in menu_items_data:
            menu_item = SidebarMenuItem(page_id, icon, label)
            self._menu_items[page_id] = menu_item
            layout.addWidget(menu_item)
            
        # Vertical spacer to push bottom content down
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Progress indicator
        self._progress_label = QLabel("Step 10 / 50")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet("color: #616161; font-size: 12px;")
        layout.addWidget(self._progress_label)
        
        # Version label at bottom
        self._version_label = QLabel("v0.1.0")
        self._version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._version_label.setStyleSheet("color: #616161; font-size: 12px;")
        layout.addWidget(self._version_label)
        
    def _setup_animation(self) -> None:
        """Setup the collapse/expand animation."""
        self._animation = QPropertyAnimation(self, b"maximumWidth")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._collapse_button.clicked.connect(self._toggle_collapse)
        
        # Connect menu item signals
        for menu_item in self._menu_items.values():
            menu_item.clicked.connect(self._on_menu_item_clicked)
            
    def _toggle_collapse(self) -> None:
        """Toggle sidebar collapse state with animation."""
        if self._is_collapsed:
            self._expand()
        else:
            self._collapse()
            
    def _collapse(self) -> None:
        """Collapse sidebar to icon-only view."""
        self._is_collapsed = True
        self._collapse_button.setText("▶")
        
        # Hide text labels
        for menu_item in self._menu_items.values():
            menu_item._text_label.setVisible(False)
            menu_item._indicator.setVisible(False)
            
        self._progress_label.setVisible(False)
        self._version_label.setVisible(False)
        
        # Animate width change
        self._animation.setStartValue(220)
        self._animation.setEndValue(56)
        self._animation.start()
        
        self._logger.debug("Sidebar collapsed")
        
    def _expand(self) -> None:
        """Expand sidebar to full view."""
        self._is_collapsed = False
        self._collapse_button.setText("◀")
        
        # Show text labels
        for menu_item in self._menu_items.values():
            menu_item._text_label.setVisible(True)
            if menu_item.is_active():
                menu_item._indicator.setVisible(True)
                
        self._progress_label.setVisible(True)
        self._version_label.setVisible(True)
        
        # Animate width change
        self._animation.setStartValue(56)
        self._animation.setEndValue(220)
        self._animation.start()
        
        self._logger.debug("Sidebar expanded")
        
    def _on_menu_item_clicked(self, page_id: PageID) -> None:
        """Handle menu item click."""
        self.navigate_to(page_id)
        
    def navigate_to(self, page_id: PageID) -> None:
        """
        Navigate to a specific page.
        
        Args:
            page_id: The page to navigate to
        """
        # Deactivate all menu items
        for menu_item in self._menu_items.values():
            menu_item.set_active(False)
            
        # Activate the target menu item
        if page_id in self._menu_items:
            self._menu_items[page_id].set_active(True)
            self._current_page = page_id
            
        # Emit page changed signal
        self.page_changed.emit(page_id)
        self._logger.info(f"Navigated to page: {page_id.value}")
        
    def set_step_progress(self, completed: int, total: int = 50) -> None:
        """
        Update the step progress indicator.
        
        Args:
            completed: Number of completed steps
            total: Total number of steps
        """
        self._progress_label.setText(f"Step {completed} / {total}")
        self._logger.debug(f"Progress updated: {completed}/{total}")
        
    def get_current_page(self) -> PageID:
        """Return the currently active page ID."""
        return self._current_page