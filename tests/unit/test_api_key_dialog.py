"""
Tests for the API key dialog implementation.

This module tests the APIKeyDialog class functionality including provider selection,
key input validation, connection testing, and key saving operations.
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QComboBox, QPushButton, QLineEdit, QDialog
from PyQt6.QtCore import Qt

from ui.dialogs.api_key_dialog import APIKeyDialog
from core.key_manager import KeyManager
from core.providers.provider_factory import ProviderFactory


class TestAPIKeyDialog:
    """Test cases for APIKeyDialog class."""
    
    @pytest.fixture
    def mock_key_manager(self):
        """Create a mock KeyManager instance."""
        mock = MagicMock(spec=KeyManager)
        mock.exists.return_value = False
        mock.save.return_value = None
        return mock
    
    @pytest.fixture
    def mock_provider_factory(self):
        """Create a mock ProviderFactory instance."""
        mock = MagicMock(spec=ProviderFactory)
        return mock
    
    @pytest.fixture
    def api_dialog(self, qtbot, mock_key_manager, mock_provider_factory):
        """Create an APIKeyDialog instance for testing."""
        dialog = APIKeyDialog(mock_key_manager, mock_provider_factory)
        qtbot.addWidget(dialog)
        return dialog
    
    def test_dialog_opens_without_error(self, api_dialog):
        """Test that dialog instantiates without error."""
        assert api_dialog is not None
        assert api_dialog.windowTitle() == "AI Provider 연결 설정"
        assert api_dialog.width() == 480
        assert api_dialog.isModal() is True
    
    def test_provider_combobox_has_three_items(self, api_dialog):
        """Test that provider combobox contains required items."""
        combo = api_dialog._provider_combo
        assert isinstance(combo, QComboBox)
        assert combo.count() == 3
        
        items = [combo.itemText(i) for i in range(combo.count())]
        assert "Claude" in items
        assert "OpenAI" in items
        assert "Gemini" in items
    
    def test_save_button_disabled_initially(self, api_dialog):
        """Test that save button is disabled on open."""
        save_button = api_dialog._save_button
        assert isinstance(save_button, QPushButton)
        assert save_button.isEnabled() is False
        assert save_button.objectName() == "primaryBtn"
    
    def test_test_button_disabled_when_key_empty(self, api_dialog):
        """Test that test button is disabled when key field is empty."""
        test_button = api_dialog._test_button
        key_input = api_dialog._key_input
        
        assert isinstance(test_button, QPushButton)
        assert isinstance(key_input, QLineEdit)
        
        # Initially empty
        assert test_button.isEnabled() is False
        
        # Still disabled with whitespace only
        key_input.setText("   ")
        assert test_button.isEnabled() is False
    
    def test_toggle_show_hide_key(self, api_dialog, qtbot):
        """Test that show/hide toggle changes echo mode."""
        key_input = api_dialog._key_input
        toggle_button = api_dialog._toggle_button
        
        # Initially should be password mode
        assert key_input.echoMode() == QLineEdit.EchoMode.Password
        assert toggle_button.text() == "👁 보기"
        
        # Click toggle to show
        qtbot.mouseClick(toggle_button, Qt.MouseButton.LeftButton)
        
        assert key_input.echoMode() == QLineEdit.EchoMode.Normal
        assert toggle_button.text() == "🙈 숨기기"
        
        # Click toggle to hide again
        qtbot.mouseClick(toggle_button, Qt.MouseButton.LeftButton)
        
        assert key_input.echoMode() == QLineEdit.EchoMode.Password
        assert toggle_button.text() == "👁 보기"
    
    def test_key_saved_signal_emitted(self, api_dialog, qtbot, mock_key_manager):
        """Test that key_saved signal is emitted with correct data."""
        # Setup for successful test scenario
        api_dialog._key_input.setText("test-api-key-12345")
        api_dialog._provider_combo.setCurrentText("Claude")
        
        # Enable save button (simulate successful test)
        api_dialog._save_button.setEnabled(True)
        
        # Connect signal spy
        with qtbot.waitSignal(api_dialog.key_saved, timeout=1000) as blocker:
            # Click save button
            qtbot.mouseClick(api_dialog._save_button, Qt.MouseButton.LeftButton)
        
        # Verify signal was emitted with correct parameters
        assert blocker.signal_triggered
        emitted_args = blocker.args
        assert len(emitted_args) == 2
        provider_name, masked_key = emitted_args
        assert provider_name == "Claude"
        assert masked_key == "test****"  # First 4 chars + "****"
        
        # Verify key manager was called
        mock_key_manager.save.assert_called_once_with("claude", "test-api-key-12345")
    
    def test_cancel_closes_dialog(self, api_dialog, qtbot):
        """Test that cancel button closes dialog with rejected result."""
        cancel_button = api_dialog._cancel_button
        
        # Click cancel button
        with qtbot.waitSignal(api_dialog.finished, timeout=1000):
            qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
        
        # Dialog should be rejected
        assert api_dialog.result() == QDialog.DialogCode.Rejected