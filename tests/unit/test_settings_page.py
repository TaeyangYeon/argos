"""
Unit tests for the SettingsPage component.

Tests UI creation, widget interactions, validation, and settings persistence
with proper mocking of file system dependencies.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from ui.pages.settings_page import SettingsPage
from config.settings import Settings
from config.constants import DEFAULT_SCORE_THRESHOLD


@pytest.fixture
def app(qtbot):
    """Create QApplication instance for tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def settings_page(qtbot, tmp_path):
    """Create SettingsPage instance with mocked SETTINGS_FILE."""
    with patch('ui.pages.settings_page.SETTINGS_FILE', tmp_path / 'settings.json'):
        page = SettingsPage()
        qtbot.addWidget(page)
        return page


@pytest.fixture
def default_settings():
    """Create default Settings instance."""
    return Settings()


class TestSettingsPageCreation:
    """Test settings page creation and initialization."""
    
    def test_settings_page_created(self, settings_page):
        """SettingsPage instantiates without error."""
        assert settings_page is not None
        assert settings_page.windowTitle() == ""
        assert settings_page._is_dirty is False
        
    def test_page_has_header(self, settings_page):
        """Page has proper header with title and subtitle."""
        assert settings_page._header is not None
        assert "설정" in settings_page._header._title_label.text()
        
    def test_page_has_toast(self, qtbot, settings_page):
        """Page has toast notification component after proper initialization."""
        # Toast is created lazily when first needed in _ensure_toast method
        # Initially it should be None
        assert settings_page._toast is None
        
        # After calling _ensure_toast, it should be created
        settings_page._ensure_toast()
        assert settings_page._toast is not None


class TestThresholdControls:
    """Test threshold slider and spinbox functionality."""
    
    def test_default_threshold_value(self, settings_page):
        """Threshold slider default value equals DEFAULT_SCORE_THRESHOLD."""
        assert settings_page._threshold_slider.value() == int(DEFAULT_SCORE_THRESHOLD)
        assert settings_page._threshold_spinbox.value() == int(DEFAULT_SCORE_THRESHOLD)
        
    def test_threshold_slider_range(self, settings_page):
        """Slider min=50, max=95."""
        assert settings_page._threshold_slider.minimum() == 50
        assert settings_page._threshold_slider.maximum() == 95
        
    def test_threshold_spinbox_range(self, settings_page):
        """Spinbox min=50, max=95."""
        assert settings_page._threshold_spinbox.minimum() == 50
        assert settings_page._threshold_spinbox.maximum() == 95
        
    def test_threshold_slider_sync_to_spinbox(self, qtbot, settings_page):
        """Threshold slider changes update spinbox."""
        settings_page._threshold_slider.setValue(75)
        assert settings_page._threshold_spinbox.value() == 75
        
    def test_threshold_spinbox_sync_to_slider(self, qtbot, settings_page):
        """Threshold spinbox changes update slider."""
        settings_page._threshold_spinbox.setValue(85)
        assert settings_page._threshold_slider.value() == 85
        
    def test_threshold_status_updates(self, qtbot, settings_page):
        """Threshold status label updates with value changes."""
        # Test low threshold (< 60)
        settings_page._threshold_slider.setValue(55)
        assert "낮음" in settings_page._threshold_status_label.text()
        
        # Test recommended threshold (60-80)
        settings_page._threshold_slider.setValue(70)
        assert "권장" in settings_page._threshold_status_label.text()
        
        # Test strict threshold (> 80)
        settings_page._threshold_slider.setValue(90)
        assert "엄격" in settings_page._threshold_status_label.text()


class TestWeightControls:
    """Test OK/NG weight sliders synchronization."""
    
    def test_weight_sync_w1_changes_w2(self, qtbot, settings_page):
        """Set w1 slider to 70 → w2 slider updates to 30."""
        settings_page._ok_weight_slider.setValue(70)
        assert settings_page._ng_weight_slider.value() == 30
        
    def test_weight_sync_w2_changes_w1(self, qtbot, settings_page):
        """Set w2 slider to 30 → w1 slider updates to 70."""
        settings_page._ng_weight_slider.setValue(30)
        assert settings_page._ok_weight_slider.value() == 70
        
    def test_weight_sum_always_100(self, qtbot, settings_page):
        """After any slider change, w1 + w2 == 100."""
        # Test multiple combinations
        test_values = [20, 45, 60, 80, 90]
        
        for value in test_values:
            settings_page._ok_weight_slider.setValue(value)
            total = settings_page._ok_weight_slider.value() + settings_page._ng_weight_slider.value()
            assert total == 100
            
            settings_page._ng_weight_slider.setValue(value)
            total = settings_page._ok_weight_slider.value() + settings_page._ng_weight_slider.value()
            assert total == 100
            
    def test_formula_preview_updates(self, qtbot, settings_page):
        """Formula preview updates when weights change."""
        settings_page._ok_weight_slider.setValue(60)
        formula_text = settings_page._formula_label.text()
        assert "0.6" in formula_text and "0.4" in formula_text
        
        settings_page._ng_weight_slider.setValue(30)
        formula_text = settings_page._formula_label.text()
        # When NG slider is 30, OK slider should be 70
        # So w1=0.7 and w2=0.3
        assert "0.7" in formula_text and "0.3" in formula_text


class TestMarginControls:
    """Test margin slider and spinbox functionality."""
    
    def test_margin_slider_range(self, settings_page):
        """Margin slider min=5, max=30."""
        assert settings_page._margin_slider.minimum() == 5
        assert settings_page._margin_slider.maximum() == 30
        
    def test_margin_spinbox_range(self, settings_page):
        """Margin spinbox min=5, max=30."""
        assert settings_page._margin_spinbox.minimum() == 5
        assert settings_page._margin_spinbox.maximum() == 30
        
    def test_margin_slider_sync_to_spinbox(self, qtbot, settings_page):
        """Margin slider changes update spinbox."""
        settings_page._margin_slider.setValue(20)
        assert settings_page._margin_spinbox.value() == 20
        
    def test_margin_spinbox_sync_to_slider(self, qtbot, settings_page):
        """Margin spinbox changes update slider."""
        settings_page._margin_spinbox.setValue(25)
        assert settings_page._margin_slider.value() == 25


class TestSettingsManagement:
    """Test settings loading, saving, and retrieval."""
    
    def test_get_current_settings_returns_settings(self, settings_page):
        """get_current_settings() returns Settings instance."""
        current = settings_page.get_current_settings()
        assert isinstance(current, Settings)
        
    def test_get_current_settings_threshold(self, settings_page):
        """Set slider to 75 → get_current_settings().score_threshold == 75."""
        settings_page._threshold_slider.setValue(75)
        current = settings_page.get_current_settings()
        assert current.score_threshold == 75.0
        
    def test_get_current_settings_weights(self, settings_page):
        """Weight values are correctly converted to float."""
        settings_page._ok_weight_slider.setValue(60)  # Should be 0.6
        settings_page._ng_weight_slider.setValue(40)  # Should be 0.4
        
        current = settings_page.get_current_settings()
        assert abs(current.w1 - 0.6) < 1e-6
        assert abs(current.w2 - 0.4) < 1e-6
        
    def test_get_current_settings_all_values(self, settings_page):
        """All widget values are correctly captured in Settings."""
        # Set specific values
        settings_page._threshold_slider.setValue(85)
        settings_page._margin_slider.setValue(20)
        settings_page._ok_weight_slider.setValue(70)
        settings_page._ng_min_recommended_spinbox.setValue(5)
        settings_page._ng_absolute_min_spinbox.setValue(2)
        settings_page._ai_timeout_spinbox.setValue(45)
        settings_page._ai_retry_spinbox.setValue(3)
        settings_page._log_dir_edit.setText("/custom/logs")
        settings_page._output_dir_edit.setText("/custom/output")
        
        current = settings_page.get_current_settings()
        
        assert current.score_threshold == 85.0
        assert current.margin_warning == 20.0
        assert abs(current.w1 - 0.7) < 1e-6
        assert abs(current.w2 - 0.3) < 1e-6
        assert current.ng_minimum_recommended == 5
        assert current.ng_absolute_minimum == 2
        assert current.ai_timeout == 45
        assert current.ai_retry == 3
        assert current.log_dir == "/custom/logs"
        assert current.output_dir == "/custom/output"


class TestDirtyState:
    """Test dirty state tracking and title updates."""
    
    def test_initial_clean_state(self, settings_page):
        """Initial state is clean."""
        assert settings_page._is_dirty is False
        assert "*" not in settings_page._header._title_label.text()
        
    def test_dirty_state_on_change(self, qtbot, settings_page):
        """Change any slider → title contains '*'."""
        settings_page._threshold_slider.setValue(80)
        assert settings_page._is_dirty is True
        assert "*" in settings_page._header._title_label.text()
        
    def test_multiple_changes_stay_dirty(self, qtbot, settings_page):
        """Multiple changes keep dirty state."""
        settings_page._threshold_slider.setValue(80)
        settings_page._ok_weight_slider.setValue(60)
        settings_page._margin_slider.setValue(20)
        
        assert settings_page._is_dirty is True
        assert "*" in settings_page._header._title_label.text()
        
    @patch('ui.pages.settings_page.SETTINGS_FILE')
    def test_clean_state_after_save(self, mock_settings_file, qtbot, settings_page):
        """Change slider → save → title does not contain '*'."""
        # Mock file operations
        mock_settings_file.exists.return_value = False
        
        # Make changes
        settings_page._threshold_slider.setValue(80)
        assert settings_page._is_dirty is True
        
        # Mock successful save
        with patch.object(Settings, 'save') as mock_save:
            QTest.mouseClick(settings_page._save_button, Qt.MouseButton.LeftButton)
            
            # Should be clean after save
            assert settings_page._is_dirty is False
            assert "*" not in settings_page._header._title_label.text()


class TestResetFunctionality:
    """Test reset to defaults functionality."""
    
    @patch('ui.pages.settings_page.QMessageBox')
    def test_reset_restores_defaults(self, mock_msgbox, qtbot, settings_page, default_settings):
        """Change threshold to 90 → reset (confirm) → slider value == DEFAULT_SCORE_THRESHOLD."""
        # Mock user confirming reset
        mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes
        
        # Change value from default
        settings_page._threshold_slider.setValue(90)
        assert settings_page._threshold_slider.value() != int(DEFAULT_SCORE_THRESHOLD)
        
        # Reset to defaults
        QTest.mouseClick(settings_page._reset_button, Qt.MouseButton.LeftButton)
        
        # Should be back to default
        assert settings_page._threshold_slider.value() == int(DEFAULT_SCORE_THRESHOLD)
        assert settings_page._is_dirty is True  # Should be dirty but not saved
        
    @patch('ui.pages.settings_page.QMessageBox')
    def test_reset_cancelled_no_change(self, mock_msgbox, qtbot, settings_page):
        """Reset cancelled → no changes made."""
        # Mock user cancelling reset
        mock_msgbox.question.return_value = mock_msgbox.StandardButton.No
        
        # Change value
        original_value = 90
        settings_page._threshold_slider.setValue(original_value)
        
        # Try to reset but cancel
        QTest.mouseClick(settings_page._reset_button, Qt.MouseButton.LeftButton)
        
        # Should remain unchanged
        assert settings_page._threshold_slider.value() == original_value
        
    @patch('ui.pages.settings_page.QMessageBox')
    def test_reset_all_values_to_defaults(self, mock_msgbox, qtbot, settings_page, default_settings):
        """Reset changes all values to defaults."""
        # Mock user confirming reset
        mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes
        
        # Change multiple values
        settings_page._threshold_slider.setValue(90)
        settings_page._ok_weight_slider.setValue(80)
        settings_page._margin_slider.setValue(25)
        settings_page._ng_min_recommended_spinbox.setValue(10)
        settings_page._ai_timeout_spinbox.setValue(60)
        
        # Reset to defaults
        QTest.mouseClick(settings_page._reset_button, Qt.MouseButton.LeftButton)
        
        # All values should match defaults
        assert settings_page._threshold_slider.value() == int(default_settings.score_threshold)
        assert settings_page._ok_weight_slider.value() == int(default_settings.w1 * 100)
        assert settings_page._ng_weight_slider.value() == int(default_settings.w2 * 100)
        assert settings_page._margin_slider.value() == int(default_settings.margin_warning)
        assert settings_page._ng_min_recommended_spinbox.value() == default_settings.ng_minimum_recommended
        assert settings_page._ai_timeout_spinbox.value() == default_settings.ai_timeout


class TestSignalsAndEvents:
    """Test signal emission and event handling."""
    
    @patch('ui.pages.settings_page.SETTINGS_FILE')
    def test_settings_saved_signal(self, mock_settings_file, qtbot, settings_page):
        """Click 저장 → settings_saved signal emitted."""
        # Mock file operations
        mock_settings_file.exists.return_value = False
        
        # Set up signal spy
        with qtbot.waitSignal(settings_page.settings_saved, timeout=1000) as blocker:
            # Mock successful save
            with patch.object(Settings, 'save'):
                QTest.mouseClick(settings_page._save_button, Qt.MouseButton.LeftButton)
            
        # Signal should have been emitted with Settings object
        assert len(blocker.args) == 1
        assert isinstance(blocker.args[0], Settings)
        
    def test_save_validation_error_handling(self, settings_page):
        """Save with invalid settings handles error gracefully."""
        # Mock validation error
        with patch.object(Settings, 'validate', side_effect=ValueError("Test validation error")):
            # Should not raise exception
            try:
                settings_page._save_settings()
            except:
                pytest.fail("_save_settings should handle validation errors gracefully")
                
    def test_save_success_handling(self, settings_page):
        """Successful save works correctly."""
        with patch.object(Settings, 'save'):
            # Should not raise exception
            try:
                settings_page._save_settings()
                assert not settings_page._is_dirty  # Should mark as clean
            except:
                pytest.fail("_save_settings should work with valid settings")


class TestSettingsLoading:
    """Test settings loading from file."""
    
    @patch('ui.pages.settings_page.SETTINGS_FILE')
    def test_load_existing_settings_file(self, mock_settings_file, settings_page, tmp_path):
        """Load settings from existing file."""
        # Create a test settings file
        test_settings = Settings(score_threshold=85.0, w1=0.7, w2=0.3)
        settings_file = tmp_path / "test_settings.json"
        test_settings.save(str(settings_file))
        
        # Mock file existence and path
        mock_settings_file.exists.return_value = True
        
        with patch.object(Settings, 'load', return_value=test_settings) as mock_load:
            settings_page.load_settings()
            
            # Settings should be loaded and applied to UI
            mock_load.assert_called_once()
            assert settings_page._threshold_slider.value() == 85
            assert settings_page._ok_weight_slider.value() == 70
            assert not settings_page._is_dirty
            
    @patch('ui.pages.settings_page.SETTINGS_FILE') 
    def test_load_nonexistent_settings_file(self, mock_settings_file, settings_page):
        """Load defaults when settings file doesn't exist."""
        # Mock file not existing
        mock_settings_file.exists.return_value = False
        
        settings_page.load_settings()
        
        # Should use defaults
        assert settings_page._threshold_slider.value() == int(DEFAULT_SCORE_THRESHOLD)
        assert not settings_page._is_dirty
        
    @patch('ui.pages.settings_page.SETTINGS_FILE')
    def test_load_settings_error_uses_defaults(self, mock_settings_file, settings_page):
        """Loading error falls back to defaults."""
        # Mock file exists but loading fails
        mock_settings_file.exists.return_value = True
        
        with patch.object(Settings, 'load', side_effect=Exception("Load error")):
            settings_page.load_settings()
            
            # Should use defaults
            assert settings_page._threshold_slider.value() == int(DEFAULT_SCORE_THRESHOLD)
            assert not settings_page._is_dirty


class TestPathSelection:
    """Test directory path selection functionality."""
    
    def test_log_directory_edit_exists(self, settings_page):
        """Log directory edit field exists and has default value."""
        assert settings_page._log_dir_edit is not None
        assert settings_page._log_dir_edit.text() == "logs/"
        
    def test_output_directory_edit_exists(self, settings_page):
        """Output directory edit field exists and has default value."""
        assert settings_page._output_dir_edit is not None
        assert settings_page._output_dir_edit.text() == "output/"