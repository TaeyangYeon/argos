"""
Unit tests for configuration and settings management.

Tests verify settings validation, serialization/deserialization,
path management, and proper error handling.
"""

import json
import tempfile
import pytest
from pathlib import Path

from config.constants import (
    DEFAULT_SCORE_THRESHOLD,
    DEFAULT_MARGIN_WARNING,
    DEFAULT_W1,
    DEFAULT_W2,
    NG_MINIMUM_RECOMMENDED,
    NG_ABSOLUTE_MINIMUM,
    AI_TIMEOUT_SECONDS,
    AI_RETRY_COUNT
)
from config.settings import Settings
from config.paths import (
    PROJECT_ROOT,
    CONFIG_DIR,
    LOGS_DIR,
    OUTPUT_DIR,
    SETTINGS_FILE,
    FIXTURES_DIR
)


class TestDefaultSettings:
    """Test Settings default values match constants."""
    
    def test_default_settings_values(self):
        """Test all default values match constants from constants.py."""
        settings = Settings()
        
        assert settings.score_threshold == DEFAULT_SCORE_THRESHOLD
        assert settings.margin_warning == DEFAULT_MARGIN_WARNING
        assert settings.w1 == DEFAULT_W1
        assert settings.w2 == DEFAULT_W2
        assert settings.ng_minimum_recommended == NG_MINIMUM_RECOMMENDED
        assert settings.ng_absolute_minimum == NG_ABSOLUTE_MINIMUM
        assert settings.ai_timeout == AI_TIMEOUT_SECONDS
        assert settings.ai_retry == AI_RETRY_COUNT
        assert settings.log_dir == "logs"
        assert settings.output_dir == "output"


class TestSettingsSerialization:
    """Test Settings save and load functionality."""
    
    def test_settings_save_and_load(self):
        """Test save to temporary file, load back, and verify equality."""
        original_settings = Settings(
            score_threshold=80.0,
            margin_warning=20.0,
            w1=0.6,
            w2=0.4,
            ai_timeout=45
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save settings
            original_settings.save(temp_path)
            
            # Load settings back
            loaded_settings = Settings.load(temp_path)
            
            # Verify all fields match
            assert loaded_settings.score_threshold == 80.0
            assert loaded_settings.margin_warning == 20.0
            assert loaded_settings.w1 == 0.6
            assert loaded_settings.w2 == 0.4
            assert loaded_settings.ai_timeout == 45
            assert loaded_settings == original_settings
        
        finally:
            Path(temp_path).unlink()
    
    def test_save_creates_pretty_json(self):
        """Test save creates properly formatted JSON with indentation."""
        settings = Settings(score_threshold=75.0)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            settings.save(temp_path)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check it's properly formatted (has newlines and indentation)
            assert '\n' in content
            assert '  ' in content  # 2-space indentation
            
            # Verify it's valid JSON
            parsed = json.loads(content)
            assert parsed['score_threshold'] == 75.0
        
        finally:
            Path(temp_path).unlink()


class TestSettingsValidation:
    """Test Settings validation logic."""
    
    def test_settings_validate_valid(self):
        """Test valid settings pass validation without exception."""
        settings = Settings(
            score_threshold=75.0,
            w1=0.7,
            w2=0.3,
            ai_timeout=30,
            ai_retry=2,
            margin_warning=10.0
        )
        
        # Should not raise any exception
        settings.validate()
    
    def test_settings_validate_invalid_threshold_low(self):
        """Test score_threshold=49 raises ValueError."""
        settings = Settings(score_threshold=49.0)
        
        with pytest.raises(ValueError, match=r"score_threshold must be between 50\.0 and 95\.0"):
            settings.validate()
    
    def test_settings_validate_invalid_threshold_high(self):
        """Test score_threshold=96 raises ValueError."""
        settings = Settings(score_threshold=96.0)
        
        with pytest.raises(ValueError, match=r"score_threshold must be between 50\.0 and 95\.0"):
            settings.validate()
    
    def test_settings_validate_invalid_weights(self):
        """Test w1=0.3, w2=0.3 (sum != 1.0) raises ValueError."""
        settings = Settings(w1=0.3, w2=0.3)
        
        with pytest.raises(ValueError, match=r"w1 \+ w2 must equal 1\.0"):
            settings.validate()
    
    def test_settings_validate_negative_timeout(self):
        """Test negative ai_timeout raises ValueError."""
        settings = Settings(ai_timeout=-5)
        
        with pytest.raises(ValueError, match=r"ai_timeout must be positive"):
            settings.validate()
    
    def test_settings_validate_negative_retry(self):
        """Test negative ai_retry raises ValueError."""
        settings = Settings(ai_retry=-1)
        
        with pytest.raises(ValueError, match=r"ai_retry must be non-negative"):
            settings.validate()
    
    def test_settings_validate_negative_margin(self):
        """Test negative margin_warning raises ValueError."""
        settings = Settings(margin_warning=-5.0)
        
        with pytest.raises(ValueError, match=r"margin_warning must be non-negative"):
            settings.validate()
    
    def test_settings_validate_invalid_ng_minimum(self):
        """Test ng_absolute_minimum=0 raises ValueError."""
        settings = Settings(ng_absolute_minimum=0)
        
        with pytest.raises(ValueError, match=r"ng_absolute_minimum must be at least 1"):
            settings.validate()
    
    def test_settings_validate_ng_recommended_less_than_absolute(self):
        """Test ng_minimum_recommended < ng_absolute_minimum raises ValueError."""
        settings = Settings(ng_absolute_minimum=3, ng_minimum_recommended=2)
        
        with pytest.raises(ValueError, match=r"ng_minimum_recommended.*must be.*ng_absolute_minimum"):
            settings.validate()


class TestSettingsReset:
    """Test Settings reset functionality."""
    
    def test_settings_reset(self):
        """Test reset() returns Settings instance with default values."""
        reset_settings = Settings.reset()
        default_settings = Settings()
        
        assert reset_settings == default_settings
        assert reset_settings.score_threshold == DEFAULT_SCORE_THRESHOLD
        assert reset_settings.w1 == DEFAULT_W1
        assert reset_settings.w2 == DEFAULT_W2


class TestPaths:
    """Test path configuration."""
    
    def test_paths_exist(self):
        """Test PROJECT_ROOT, CONFIG_DIR, LOGS_DIR, OUTPUT_DIR all exist."""
        assert PROJECT_ROOT.exists(), f"PROJECT_ROOT does not exist: {PROJECT_ROOT}"
        assert PROJECT_ROOT.is_dir(), f"PROJECT_ROOT is not a directory: {PROJECT_ROOT}"
        
        assert CONFIG_DIR.exists(), f"CONFIG_DIR does not exist: {CONFIG_DIR}"
        assert CONFIG_DIR.is_dir(), f"CONFIG_DIR is not a directory: {CONFIG_DIR}"
        
        assert LOGS_DIR.exists(), f"LOGS_DIR does not exist: {LOGS_DIR}"
        assert LOGS_DIR.is_dir(), f"LOGS_DIR is not a directory: {LOGS_DIR}"
        
        assert OUTPUT_DIR.exists(), f"OUTPUT_DIR does not exist: {OUTPUT_DIR}"
        assert OUTPUT_DIR.is_dir(), f"OUTPUT_DIR is not a directory: {OUTPUT_DIR}"
    
    def test_paths_are_absolute(self):
        """Test all paths are absolute."""
        assert PROJECT_ROOT.is_absolute()
        assert CONFIG_DIR.is_absolute()
        assert LOGS_DIR.is_absolute()
        assert OUTPUT_DIR.is_absolute()
        assert SETTINGS_FILE.is_absolute()
        assert FIXTURES_DIR.is_absolute()
    
    def test_path_relationships(self):
        """Test path parent-child relationships are correct."""
        assert CONFIG_DIR.parent == PROJECT_ROOT
        assert LOGS_DIR.parent == PROJECT_ROOT
        assert OUTPUT_DIR.parent == PROJECT_ROOT
        assert SETTINGS_FILE.parent == CONFIG_DIR