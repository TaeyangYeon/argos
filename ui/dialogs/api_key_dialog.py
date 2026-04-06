"""
API Key input dialog for the Argos vision algorithm design application.

This module provides a secure modal dialog for entering and testing AI provider
API keys with real-time validation and connection testing.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QWidget, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont
import threading
from typing import Optional

from core.key_manager import KeyManager
from core.providers.provider_factory import ProviderFactory
from core.providers.base_provider import ProviderStatus
from core.logger import get_logger


class ConnectionTestWorker(QThread):
    """Worker thread for testing API connection without blocking UI."""
    
    # Signals for test results
    test_completed = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self, provider_factory: ProviderFactory, provider_name: str, api_key: str):
        super().__init__()
        self.provider_factory = provider_factory
        self.provider_name = provider_name
        self.api_key = api_key
        self._logger = get_logger("api_dialog")
        
    def run(self):
        """Run the connection test in background thread."""
        try:
            # Create provider and test connection
            provider = self.provider_factory.create_provider(self.provider_name)
            provider.set_api_key(self.api_key)
            
            # Test the connection
            info = provider.get_provider_info()
            if info and info.status == ProviderStatus.CONNECTED:
                model_info = getattr(info, 'model_version', 'unknown')
                self.test_completed.emit(True, f"{self.provider_name.title()} ({model_info})")
            else:
                self.test_completed.emit(False, "Connection failed")
                
        except Exception as e:
            self._logger.error(f"Connection test failed: {e}")
            self.test_completed.emit(False, str(e))


class APIKeyDialog(QDialog):
    """
    Modal dialog for AI provider API key input and connection testing.
    
    Provides secure key input with show/hide toggle, provider selection,
    connection testing, and key storage functionality.
    """
    
    # Signal emitted when key is successfully saved
    key_saved = pyqtSignal(str, str)  # (provider_name, masked_key)
    
    def __init__(self, key_manager: KeyManager, provider_factory: ProviderFactory, parent=None):
        """
        Initialize the API key dialog.
        
        Args:
            key_manager: Instance for encrypted key storage
            provider_factory: Factory for creating provider instances
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.key_manager = key_manager
        self.provider_factory = provider_factory
        self._logger = get_logger("api_dialog")
        self._test_worker: Optional[ConnectionTestWorker] = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_existing_key()
        
    def _setup_ui(self) -> None:
        """Setup the dialog UI layout."""
        self.setWindowTitle("AI Provider 연결 설정")
        self.setFixedWidth(480)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title section
        title_label = QLabel("🔑 AI Provider 연결 설정")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("AI 분석 기능을 사용하려면\nAPI Key를 입력하세요.")
        subtitle_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(subtitle_label)
        
        # Provider selection
        provider_layout = QHBoxLayout()
        provider_label = QLabel("Provider")
        provider_label.setFixedWidth(80)
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["Claude", "OpenAI", "Gemini"])
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self._provider_combo)
        layout.addLayout(provider_layout)
        
        # API Key input with show/hide toggle
        key_layout = QVBoxLayout()
        key_row = QHBoxLayout()
        key_label = QLabel("API Key")
        key_label.setFixedWidth(80)
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("API Key를 입력하세요")
        key_row.addWidget(key_label)
        key_row.addWidget(self._key_input)
        
        # Show/hide toggle button
        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(QWidget())  # Spacer to align with key field
        self._toggle_button = QPushButton("👁 보기")
        self._toggle_button.setFixedWidth(80)
        self._key_visible = False
        toggle_layout.addWidget(self._toggle_button)
        
        key_layout.addLayout(key_row)
        key_layout.addLayout(toggle_layout)
        layout.addLayout(key_layout)
        
        # Connection test button
        test_layout = QHBoxLayout()
        self._test_button = QPushButton("🔗 연결 테스트")
        self._test_button.setEnabled(False)  # Disabled until key is entered
        test_layout.addWidget(self._test_button)
        test_layout.addWidget(QWidget())  # Spacer
        layout.addLayout(test_layout)
        
        # Result label (hidden initially)
        self._result_label = QLabel()
        self._result_label.setVisible(False)
        layout.addWidget(self._result_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(QWidget())  # Spacer
        
        self._save_button = QPushButton("저장")
        self._save_button.setObjectName("primaryBtn")
        self._save_button.setEnabled(False)  # Only enabled after successful test
        
        self._cancel_button = QPushButton("취소")
        
        button_layout.addWidget(self._save_button)
        button_layout.addWidget(self._cancel_button)
        layout.addLayout(button_layout)
        
    def _connect_signals(self) -> None:
        """Connect UI signals to their handlers."""
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        self._key_input.textChanged.connect(self._on_key_changed)
        self._toggle_button.clicked.connect(self._toggle_key_visibility)
        self._test_button.clicked.connect(self._test_connection)
        self._save_button.clicked.connect(self._save_key)
        self._cancel_button.clicked.connect(self.reject)
        
    def _load_existing_key(self) -> None:
        """Load existing key for the selected provider."""
        provider_name = self._provider_combo.currentText().lower()
        
        if self.key_manager.exists(provider_name):
            # Show masked placeholder to indicate existing key
            self._key_input.setPlaceholderText("••••••••••••••••••••")
            
    def _on_provider_changed(self, provider_name: str) -> None:
        """Handle provider selection change."""
        # Clear previous key and reset UI state
        self._key_input.clear()
        self._result_label.setVisible(False)
        self._save_button.setEnabled(False)
        
        # Load existing key for new provider
        self._load_existing_key()
        
    def _on_key_changed(self, text: str) -> None:
        """Handle API key input change."""
        has_key = len(text.strip()) > 0
        self._test_button.setEnabled(has_key)
        
        # Hide result label when key changes
        self._result_label.setVisible(False)
        self._save_button.setEnabled(False)
        
    def _toggle_key_visibility(self) -> None:
        """Toggle API key field visibility."""
        if self._key_visible:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_button.setText("👁 보기")
            self._key_visible = False
        else:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_button.setText("🙈 숨기기")
            self._key_visible = True
            
    def _test_connection(self) -> None:
        """Test the API connection in background thread."""
        provider_name = self._provider_combo.currentText().lower()
        api_key = self._key_input.text().strip()
        
        if not api_key:
            return
            
        # Disable test button and show testing state
        self._test_button.setEnabled(False)
        self._test_button.setText("테스트 중...")
        self._result_label.setVisible(False)
        
        # Start connection test in worker thread
        self._test_worker = ConnectionTestWorker(
            self.provider_factory, 
            provider_name, 
            api_key
        )
        self._test_worker.test_completed.connect(self._on_test_completed)
        self._test_worker.start()
        
    def _on_test_completed(self, success: bool, message: str) -> None:
        """Handle connection test completion."""
        # Re-enable test button
        self._test_button.setEnabled(True)
        self._test_button.setText("🔗 연결 테스트")
        
        # Show test result
        if success:
            result_text = f'<span style="color: #43A047;">✅ 연결 성공 — {message}</span>'
            self._save_button.setEnabled(True)
        else:
            result_text = '<span style="color: #E53935;">❌ 연결 실패 — API Key를 확인해주세요.</span>'
            self._save_button.setEnabled(False)
            
        self._result_label.setText(result_text)
        self._result_label.setVisible(True)
        
    def _save_key(self) -> None:
        """Save the API key and close dialog."""
        provider_name = self._provider_combo.currentText().lower()
        api_key = self._key_input.text().strip()
        
        if not api_key:
            return
            
        try:
            # Save the key
            self.key_manager.save(provider_name, api_key)
            
            # Create masked key for signal
            masked_key = api_key[:4] + "****" if len(api_key) > 4 else "****"
            
            # Emit signal and close dialog
            self.key_saved.emit(provider_name.title(), masked_key)
            self.accept()
            
        except Exception as e:
            self._logger.error(f"Failed to save API key: {e}")
            result_text = '<span style="color: #E53935;">❌ 저장 실패 — 다시 시도해주세요.</span>'
            self._result_label.setText(result_text)
            self._result_label.setVisible(True)