"""
Main window for the Argos vision algorithm design application.

This module provides the MainWindow class which sets up the primary application
window with dark theme, sidebar layout, and status bar.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QFrame, 
    QStackedWidget, QStatusBar, QLabel
)
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QIcon

from core.logger import get_logger
from core.key_manager import KeyManager
from core.image_store import ImageStore
from core.providers.provider_factory import ProviderFactory
from ui.style import DARK_THEME_QSS
from ui.components.toolbar import ArgosToolbar
from ui.components.sidebar import ArgosSidebar, PageID
from ui.pages.dashboard_page import DashboardPage
from ui.pages.upload_page import UploadPage
from ui.pages.roi_page import ROIPage
from ui.pages.purpose_page import PurposePage
from ui.pages.analysis_page import AnalysisPage
from ui.pages.result_page import ResultPage
from ui.pages.settings_page import SettingsPage


class MainWindow(QMainWindow):
    """
    Main application window for Argos.
    
    Provides the primary layout with sidebar navigation, content area,
    and status bar with connection status display.
    """
    
    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        
        self._logger = get_logger("main_window")
        
        # Initialize key manager, image store, and provider factory
        self.key_manager = KeyManager()
        self.image_store = ImageStore()
        self.provider_factory = ProviderFactory()
        
        # Store for inspection purpose and ROI config
        self._inspection_purpose = None
        self._roi_config = None
        
        self._setup_window()
        self._setup_toolbar()
        self._setup_layout()
        self._setup_pages()
        self._setup_status_bar()
        
    def _setup_window(self) -> None:
        """Setup window properties."""
        self.setWindowTitle("Argos — Vision Algorithm Agent")
        self.setMinimumSize(1280, 800)
        
        # Apply dark theme
        self.setStyleSheet(DARK_THEME_QSS)
        
        # Set window icon if it exists
        icon_path = Path(__file__).parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            
        self._logger.info("Main window initialized")
    
    def _setup_toolbar(self) -> None:
        """Setup the main toolbar."""
        self._toolbar = ArgosToolbar(
            self.key_manager,
            self.provider_factory,
            self
        )
        self.addToolBar(self._toolbar)
        
        # Connect toolbar signals
        self._toolbar.connection_changed.connect(self.set_connection_status)
    
    def _setup_layout(self) -> None:
        """Setup the main window layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout (no margins)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left sidebar with navigation
        self._sidebar = ArgosSidebar()
        
        # Right content area (expandable)
        self._content_area = QStackedWidget()
        self._content_area.setObjectName("content")
        
        # Add to layout
        main_layout.addWidget(self._sidebar)
        main_layout.addWidget(self._content_area)
        
    def _setup_pages(self) -> None:
        """Setup all application pages and navigation."""
        # Create all pages with required dependencies
        self._pages = {
            PageID.DASHBOARD: DashboardPage(self.image_store, self.key_manager),
            PageID.UPLOAD: UploadPage(self.image_store),
            PageID.ROI: ROIPage(self.image_store),
            PageID.PURPOSE: PurposePage(),
            PageID.ANALYSIS: AnalysisPage(self.image_store),
            PageID.RESULTS: ResultPage(),
            PageID.SETTINGS: SettingsPage(),
        }
        
        # Add pages to content area in PageID order
        for page_id in [PageID.DASHBOARD, PageID.UPLOAD, PageID.ROI, 
                       PageID.PURPOSE, PageID.ANALYSIS, PageID.RESULTS, PageID.SETTINGS]:
            self._content_area.addWidget(self._pages[page_id])
            
        # Connect sidebar navigation signal
        self._sidebar.page_changed.connect(self._on_page_changed)
        
        # Connect page navigation signals
        self._pages[PageID.DASHBOARD].navigate_requested.connect(
            lambda page_id: self._sidebar.navigate_to(PageID(page_id))
        )
        self._pages[PageID.ROI].navigate_requested.connect(
            lambda page_id: self._sidebar.navigate_to(PageID(page_id))
        )
        
        # Connect purpose page signals
        self._pages[PageID.PURPOSE].purpose_confirmed.connect(self._on_purpose_confirmed)
        
        # Connect analysis page signals
        self._pages[PageID.ANALYSIS].navigate_to_result.connect(
            lambda: self._sidebar.navigate_to(PageID.RESULTS)
        )
        
        # Connect ROI page signals to update analysis page
        self._pages[PageID.ROI].roi_confirmed.connect(self._on_roi_confirmed)
        
        # Set initial page to dashboard
        self._sidebar.navigate_to(PageID.DASHBOARD)
        
    def _on_page_changed(self, page_id: PageID) -> None:
        """
        Handle page navigation from sidebar.
        
        Args:
            page_id: The page to navigate to
        """
        if page_id in self._pages:
            page_widget = self._pages[page_id]
            page_index = self._content_area.indexOf(page_widget)
            if page_index >= 0:
                self._content_area.setCurrentIndex(page_index)
                self._logger.info(f"Switched to page: {page_id.value}")
        else:
            self._logger.error(f"Unknown page ID: {page_id}")
            
    def _on_purpose_confirmed(self, purpose) -> None:
        """
        Handle inspection purpose confirmation.
        
        Args:
            purpose: The confirmed InspectionPurpose object
        """
        self._inspection_purpose = purpose
        self._logger.info(f"Inspection purpose confirmed: {purpose.inspection_type}")
        
        # Update analysis page with new purpose
        self._pages[PageID.ANALYSIS].set_inspection_purpose(purpose)
        self._update_analysis_preflight()
        
    def _on_roi_confirmed(self, roi_config) -> None:
        """
        Handle ROI configuration confirmation.
        
        Args:
            roi_config: The confirmed ROIConfig object
        """
        self._roi_config = roi_config
        self._logger.info(f"ROI config confirmed: {roi_config}")
        
        # Update analysis page with new ROI config
        self._pages[PageID.ANALYSIS].set_roi_config(roi_config)
        self._update_analysis_preflight()
        
    def _update_analysis_preflight(self) -> None:
        """Update analysis page pre-flight check with current state."""
        self._pages[PageID.ANALYSIS].update_preflight(
            self.image_store, 
            self._roi_config, 
            self._inspection_purpose
        )
        
    def _setup_status_bar(self) -> None:
        """Setup the status bar with version info."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Version label only (connection status now handled by toolbar)
        version_label = QLabel("Argos v0.1.0")
        status_bar.addWidget(version_label)
        
    def closeEvent(self, event: QEvent) -> None:
        """Handle window close event."""
        self._on_close(event)
        
    def _on_close(self, event: QEvent) -> None:
        """Log application closing and accept the event."""
        self._logger.info("Application closing")
        event.accept()
        
    def set_connection_status(self, connected: bool, provider_name: str = "") -> None:
        """
        Update the connection status (now handled by toolbar).
        
        This method is kept for compatibility and logs status changes.
        
        Args:
            connected: Whether AI provider is connected
            provider_name: Name of the connected AI provider
        """
        self._logger.debug(f"Connection status updated: connected={connected}, provider={provider_name}")
        
    def get_content_area(self) -> QStackedWidget:
        """
        Get the content area widget for adding pages.
        
        Returns:
            The main content QStackedWidget
        """
        return self._content_area
        
    def get_sidebar(self) -> ArgosSidebar:
        """
        Get the sidebar navigation widget.
        
        Returns:
            The ArgosSidebar widget
        """
        return self._sidebar