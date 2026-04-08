"""
Tests for the feature analyzer module.

This module tests the FeatureAnalyzer class which integrates histogram,
noise, edge, and shape analysis into a unified feature analysis system.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.analyzers.feature_analyzer import FeatureAnalyzer, FullFeatureAnalysis
from core.exceptions import RuntimeProcessingError
from core.models import FeatureAnalysisSummary


class TestFeatureAnalyzer:
    """Test cases for FeatureAnalyzer class."""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        # Create 100x100 grayscale image with some structure
        image = np.zeros((100, 100), dtype=np.uint8)
        # Add some features
        image[30:70, 30:70] = 128  # Square region
        image[20:25, 20:80] = 255  # Horizontal line
        image[20:80, 75:80] = 255  # Vertical line
        return image
    
    @pytest.fixture
    def bright_image(self):
        """Create a bright test image."""
        return np.full((100, 100), 200, dtype=np.uint8)
    
    @pytest.fixture
    def dark_image(self):
        """Create a dark test image."""
        return np.full((100, 100), 50, dtype=np.uint8)
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Create a mock AI provider."""
        provider = MagicMock()
        provider.analyze_safe.return_value = "테스트 AI 요약 결과"
        return provider
    
    def test_analyze_returns_summary(self, sample_image):
        """Test that analyze() returns a FeatureAnalysisSummary."""
        analyzer = FeatureAnalyzer()
        
        result = analyzer.analyze(sample_image)
        
        assert isinstance(result, FeatureAnalysisSummary)
        assert result.ai_summary is None  # No AI provider
    
    def test_analyze_summary_fields(self, sample_image):
        """Test that all required summary fields are populated."""
        analyzer = FeatureAnalyzer()
        
        result = analyzer.analyze(sample_image)
        
        # Check all required fields are present and valid
        assert isinstance(result.mean_gray, float)
        assert isinstance(result.std_gray, float)
        assert result.noise_level in ["Low", "Medium", "High"]
        assert isinstance(result.edge_density, float)
        assert isinstance(result.blob_count, int)
        assert isinstance(result.has_circular_structure, bool)
        
        # Verify reasonable ranges
        assert 0 <= result.mean_gray <= 255
        assert result.std_gray >= 0
        assert 0 <= result.edge_density <= 1.0
        assert result.blob_count >= 0
    
    def test_analyze_full_returns_full_analysis(self, sample_image):
        """Test that analyze_full() returns a FullFeatureAnalysis."""
        analyzer = FeatureAnalyzer()
        
        result = analyzer.analyze_full(sample_image, "test_image.png")
        
        assert isinstance(result, FullFeatureAnalysis)
        assert result.image_path == "test_image.png"
        assert result.image_width == 100
        assert result.image_height == 100
        assert result.analyzed_at.endswith("Z")  # ISO format with Z suffix
        assert "Image Properties:" in result.ai_prompt
    
    def test_analyze_full_without_provider(self, sample_image):
        """Test analyze_full without AI provider uses fallback message."""
        analyzer = FeatureAnalyzer(ai_provider=None)
        
        result = analyzer.analyze_full(sample_image)
        
        assert result.summary.ai_summary == "AI 분석을 사용할 수 없습니다."
    
    def test_analyze_full_with_mock_provider(self, sample_image, mock_ai_provider):
        """Test analyze_full with mock AI provider returns AI summary."""
        analyzer = FeatureAnalyzer(ai_provider=mock_ai_provider)
        
        result = analyzer.analyze_full(sample_image)
        
        assert result.summary.ai_summary == "테스트 AI 요약 결과"
        mock_ai_provider.analyze_safe.assert_called_once()
    
    def test_analyze_full_with_provider_exception(self, sample_image):
        """Test analyze_full when AI provider raises exception."""
        failing_provider = MagicMock()
        failing_provider.analyze_safe.side_effect = Exception("API Error")
        
        analyzer = FeatureAnalyzer(ai_provider=failing_provider)
        
        result = analyzer.analyze_full(sample_image)
        
        assert result.summary.ai_summary == "AI 분석을 사용할 수 없습니다."
    
    def test_get_summary_before_analyze_raises(self):
        """Test that get_summary() raises error before any analyze() call."""
        analyzer = FeatureAnalyzer()
        
        with pytest.raises(RuntimeProcessingError) as exc_info:
            analyzer.get_summary()
        
        assert "No analysis has been performed yet" in str(exc_info.value)
    
    def test_get_summary_after_analyze(self, sample_image):
        """Test that get_summary() returns string after analyze()."""
        analyzer = FeatureAnalyzer()
        
        analyzer.analyze(sample_image)
        summary_text = analyzer.get_summary()
        
        assert isinstance(summary_text, str)
        assert "이미지 특성 분석 결과" in summary_text
        assert "평균 밝기" in summary_text
        assert "노이즈 수준" in summary_text
    
    def test_analyze_ok_ng_separation_keys(self, bright_image, dark_image):
        """Test that analyze_ok_ng_separation returns dict with required keys."""
        analyzer = FeatureAnalyzer()
        
        result = analyzer.analyze_ok_ng_separation([bright_image], [dark_image])
        
        required_keys = ["histogram_separation", "edge_comparison", "separation_score", "recommendation"]
        for key in required_keys:
            assert key in result
    
    def test_analyze_ok_ng_separation_recommendation(self, bright_image, dark_image):
        """Test recommendation logic based on separation score."""
        analyzer = FeatureAnalyzer()
        
        # Bright vs dark should have high separation score
        result = analyzer.analyze_ok_ng_separation([bright_image], [dark_image])
        
        assert isinstance(result["separation_score"], float)
        # Should recommend histogram-based since bright vs dark has good separation
        if result["separation_score"] >= 40:
            assert "히스토그램" in result["recommendation"]
    
    def test_analyze_ok_ng_empty_raises(self, sample_image):
        """Test that empty image lists raise RuntimeProcessingError."""
        analyzer = FeatureAnalyzer()
        
        # Empty OK images
        with pytest.raises(RuntimeProcessingError) as exc_info:
            analyzer.analyze_ok_ng_separation([], [sample_image])
        assert "OK images list is empty" in str(exc_info.value)
        
        # Empty NG images
        with pytest.raises(RuntimeProcessingError) as exc_info:
            analyzer.analyze_ok_ng_separation([sample_image], [])
        assert "NG images list is empty" in str(exc_info.value)
    
    def test_build_ai_prompt_contains_keywords(self, sample_image):
        """Test that _build_ai_prompt contains expected sections."""
        analyzer = FeatureAnalyzer()
        result = analyzer.analyze_full(sample_image)
        
        prompt = result.ai_prompt
        
        # Check for required sections
        assert "Image Properties:" in prompt
        assert "Noise Analysis:" in prompt
        assert "Edge Analysis:" in prompt
        assert "Shape Analysis:" in prompt
        assert "Size:" in prompt
        assert "Mean Gray:" in prompt
        assert "Korean" in prompt  # Should specify Korean output
    
    def test_save_result_creates_file(self, sample_image, tmp_path):
        """Test that save_result creates a JSON file."""
        analyzer = FeatureAnalyzer()
        result = analyzer.analyze_full(sample_image, "test.png")
        
        saved_path = analyzer.save_result(result, tmp_path)
        
        assert saved_path.exists()
        assert saved_path.suffix == ".json"
        assert saved_path.parent == tmp_path
        assert "feature_" in saved_path.name
    
    def test_save_result_json_valid(self, sample_image, tmp_path):
        """Test that saved JSON file is valid and contains expected keys."""
        analyzer = FeatureAnalyzer()
        result = analyzer.analyze_full(sample_image, "test.png")
        
        saved_path = analyzer.save_result(result, tmp_path)
        
        # Load and validate JSON
        with open(saved_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check required top-level keys
        assert "image_width" in data
        assert "image_height" in data
        assert "image_path" in data
        assert "analyzed_at" in data
        assert "summary" in data
        
        # Verify values
        assert data["image_width"] == 100
        assert data["image_height"] == 100
        assert data["image_path"] == "test.png"


class TestFeatureAnalyzerIntegration:
    """Integration tests for FeatureAnalyzer with real sample images."""
    
    @pytest.fixture
    def sample_ok_image_path(self):
        """Get path to sample OK image if it exists."""
        fixture_path = Path("tests/fixtures/sample_ok.png")
        if fixture_path.exists():
            return fixture_path
        return None
    
    @pytest.mark.skipif(not Path("tests/fixtures/sample_ok.png").exists(), 
                       reason="Sample image not available")
    def test_analyze_with_real_image(self, sample_ok_image_path):
        """Test analysis with real sample image if available."""
        import cv2
        
        analyzer = FeatureAnalyzer()
        image = cv2.imread(str(sample_ok_image_path), cv2.IMREAD_GRAYSCALE)
        
        result = analyzer.analyze(image)
        
        assert isinstance(result, FeatureAnalysisSummary)
        assert result.mean_gray >= 0
        assert result.std_gray >= 0
    
    def test_multiple_images_consistency(self):
        """Test that analyzer gives consistent results for identical images."""
        # Create identical images
        image1 = np.full((50, 50), 128, dtype=np.uint8)
        image2 = np.full((50, 50), 128, dtype=np.uint8)
        
        analyzer = FeatureAnalyzer()
        
        result1 = analyzer.analyze(image1)
        result2 = analyzer.analyze(image2)
        
        # Results should be very similar (allowing for minor floating point differences)
        assert abs(result1.mean_gray - result2.mean_gray) < 1.0
        assert abs(result1.std_gray - result2.std_gray) < 1.0
        assert result1.noise_level == result2.noise_level
    
    def test_edge_cases(self):
        """Test analyzer with edge case images."""
        analyzer = FeatureAnalyzer()
        
        # All black image
        black_image = np.zeros((50, 50), dtype=np.uint8)
        result_black = analyzer.analyze(black_image)
        assert result_black.mean_gray == 0
        assert result_black.std_gray == 0
        
        # All white image  
        white_image = np.full((50, 50), 255, dtype=np.uint8)
        result_white = analyzer.analyze(white_image)
        assert result_white.mean_gray == 255
        assert result_white.std_gray == 0
    
    def test_color_image_conversion(self):
        """Test that color images are properly converted to grayscale."""
        # Create a 3-channel color image
        color_image = np.zeros((50, 50, 3), dtype=np.uint8)
        color_image[:, :, 0] = 100  # Red channel
        color_image[:, :, 1] = 150  # Green channel  
        color_image[:, :, 2] = 200  # Blue channel
        
        analyzer = FeatureAnalyzer()
        result = analyzer.analyze(color_image)
        
        # Should have successfully analyzed without errors
        assert isinstance(result, FeatureAnalysisSummary)
        assert result.mean_gray > 0  # Should have some gray value from conversion