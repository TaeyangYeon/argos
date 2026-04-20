"""
Main toolbar component for the Argos vision algorithm design application.

This module provides the primary application toolbar with logo, connection status,
and API key input functionality.
"""

from PyQt6.QtWidgets import (
    QToolBar, QLabel, QPushButton, QWidget, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from core.key_manager import KeyManager
from core.providers.provider_factory import ProviderFactory
from core.logger import get_logger
from .status_indicator import ConnectionStatusWidget
from ..dialogs.api_key_dialog import APIKeyDialog
from ui.theme import Tooltips


class ArgosToolbar(QToolBar):
    """
    Main application toolbar with logo, status, and API key input.
    
    Provides a clean interface for displaying connection status and
    accessing API key management functionality.
    """
    
    # Signal emitted when connection status changes
    connection_changed = pyqtSignal(bool, str)  # (connected, provider_name)
    
    def __init__(self, key_manager: KeyManager, provider_factory: ProviderFactory, parent=None):
        """
        Initialize the toolbar.
        
        Args:
            key_manager: Instance for encrypted key storage
            provider_factory: Factory for creating provider instances
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.key_manager = key_manager
        self.provider_factory = provider_factory
        self._logger = get_logger("toolbar")
        
        self._setup_toolbar()
        self._setup_widgets()
        self._connect_signals()
        self._update_connection_status(None)
        
    def _setup_toolbar(self) -> None:
        """Setup toolbar properties."""
        self.setObjectName("mainToolbar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
    def _setup_widgets(self) -> None:
        """Setup toolbar widgets."""
        # Logo/Title
        logo_label = QLabel("⬡ Argos")
        logo_font = QFont()
        logo_font.setPointSize(16)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: #1E88E5; padding: 4px 8px;")
        self.addWidget(logo_label)
        
        # Spacer widget to push right-side widgets to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)
        
        # Connection status widget
        self._status_widget = ConnectionStatusWidget()
        self._status_widget.setToolTip(Tooltips.API_STATUS)
        self.addWidget(self._status_widget)
        
        # Add some spacing
        spacing_widget = QWidget()
        spacing_widget.setFixedWidth(12)
        self.addWidget(spacing_widget)
        
        # API input button
        self._api_button = QPushButton("🔑 API 입력")
        self._api_button.setObjectName("primaryBtn")
        self._api_button.setToolTip(Tooltips.API_BUTTON)
        self.addWidget(self._api_button)
        
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._api_button.clicked.connect(self._open_api_dialog)
        self._status_widget.status_changed.connect(self.connection_changed.emit)
        
    def _open_api_dialog(self) -> None:
        """Open the API key input dialog."""
        dialog = APIKeyDialog(
            self.key_manager, 
            self.provider_factory, 
            self.parent()
        )
        dialog.key_saved.connect(self._on_key_saved)
        
        if dialog.exec():
            self._logger.info("API key dialog completed successfully")
        else:
            self._logger.info("API key dialog was cancelled")
            
    def _on_key_saved(self, provider_name: str, masked_key: str) -> None:
        """
        Handle API key save completion.
        
        Args:
            provider_name: Name of the provider
            masked_key: Masked version of the API key for display
        """
        self._logger.info(f"API key saved for provider: {provider_name}")
        self._update_connection_status(provider_name)
        
    def _update_connection_status(self, provider_name: str | None) -> None:
        """
        Update connection status based on available keys.
        
        Args:
            provider_name: Name of provider to check, or None to check all
        """
        # Check if any provider has a saved key
        providers_to_check = ["claude", "openai", "gemini"]
        connected_provider = None
        
        for provider in providers_to_check:
            if self.key_manager.exists(provider):
                connected_provider = provider
                break
                
        if connected_provider:
            self._status_widget.set_connected(connected_provider.title())
        else:
            self._status_widget.set_disconnected()
            
    def update_connection_status(self, provider_name: str | None) -> None:
        """
        Public method to update connection status.
        
        Args:
            provider_name: Name of the provider that was updated
        """
        self._update_connection_status(provider_name)