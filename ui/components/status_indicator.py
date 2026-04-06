"""
Connection status indicator widget for the Argos vision algorithm design application.

This module provides a visual status indicator for AI provider connections
with colored dots and status text.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal


class ConnectionStatusWidget(QWidget):
    """
    Widget that displays connection status with colored dot and text.
    
    Shows different colored indicators for disconnected, testing, and connected states.
    Emits signals when status changes to update the main window.
    """
    
    # Signal emitted when connection status changes
    status_changed = pyqtSignal(bool, str)  # (connected, provider_name)
    
    def __init__(self, parent=None) -> None:
        """Initialize the connection status widget."""
        super().__init__(parent)
        
        self._setup_ui()
        self.set_disconnected()  # Default state
        
    def _setup_ui(self) -> None:
        """Setup the widget UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Status label with colored dot and text
        self._status_label = QLabel()
        layout.addWidget(self._status_label)
        
    def set_connected(self, provider_name: str) -> None:
        """
        Set the widget to connected state.
        
        Args:
            provider_name: Name of the connected AI provider
        """
        status_text = f'<span style="color: #43A047;">● 연결됨 ({provider_name})</span>'
        self._status_label.setText(status_text)
        self.status_changed.emit(True, provider_name)
        
    def set_disconnected(self) -> None:
        """Set the widget to disconnected state."""
        status_text = '<span style="color: #E53935;">● 미연결</span>'
        self._status_label.setText(status_text)
        self.status_changed.emit(False, "")
        
    def set_testing(self) -> None:
        """Set the widget to testing state."""
        status_text = '<span style="color: #FB8C00;">● 연결 테스트 중...</span>'
        self._status_label.setText(status_text)
        # Note: No signal emission during testing state