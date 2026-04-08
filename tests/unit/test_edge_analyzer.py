"""
Unit tests for EdgeAnalyzer.

Tests edge strength analysis, directional analysis, Canny threshold calculation,
and caliper suitability assessment with various synthetic image patterns.
"""

import pytest
import numpy as np

from core.analyzers.edge_analyzer import EdgeAnalyzer, EdgeAnalysisResult
from core.exceptions import RuntimeProcessingError


class TestEdgeAnalyzer:
    """Test cases for EdgeAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Provide EdgeAnalyzer instance."""
        return EdgeAnalyzer()
    
    @pytest.fixture
    def flat_image(self):
        """Provide flat grayscale image."""
        return np.ones((100, 100), dtype=np.uint8) * 128
    
    @pytest.fixture
    def vertical_edge_image(self):
        """Provide image with strong vertical edge (left half=0, right half=255)."""
        img = np.zeros((100, 100), dtype=np.uint8)
        img[:, 50:] = 255
        return img
    
    @pytest.fixture
    def horizontal_edge_image(self):
        """Provide image with strong horizontal edge (top half=0, bottom half=255)."""
        img = np.zeros((100, 100), dtype=np.uint8)
        img[50:, :] = 255
        return img
    
    @pytest.fixture
    def bgr_image(self):
        """Provide BGR color image."""
        return np.ones((100, 100, 3), dtype=np.uint8) * 128
    
    def test_analyze_returns_result(self, analyzer, flat_image):
        """Test that analyze returns EdgeAnalysisResult."""
        result = analyzer.analyze(flat_image)
        assert isinstance(result, EdgeAnalysisResult)
    
    def test_analyze_bgr_input(self, analyzer, bgr_image):
        """Test that analyze works with BGR input."""
        result = analyzer.analyze(bgr_image)
        assert isinstance(result, EdgeAnalysisResult)
    
    def test_analyze_grayscale_input(self, analyzer, flat_image):
        """Test that analyze works with grayscale input."""
        result = analyzer.analyze(flat_image)
        assert isinstance(result, EdgeAnalysisResult)
    
    def test_mean_edge_strength_flat_image(self, analyzer, flat_image):
        """Test that flat image has low mean edge strength."""
        result = analyzer.analyze(flat_image)
        assert result.mean_edge_strength < 1.0
    
    def test_mean_edge_strength_edge_image(self, analyzer, vertical_edge_image):
        """Test that image with strong edge has high mean edge strength."""
        result = analyzer.analyze(vertical_edge_image)
        assert result.mean_edge_strength > 10.0
    
    def test_edge_density_flat_image(self, analyzer, flat_image):
        """Test that flat image has low edge density."""
        result = analyzer.analyze(flat_image)
        assert result.edge_density < 0.01
    
    def test_edge_density_edge_image(self, analyzer, vertical_edge_image):
        """Test that edge image has non-zero edge density."""
        result = analyzer.analyze(vertical_edge_image)
        assert result.edge_density > 0.0
    
    def test_dominant_direction_vertical_edge(self, analyzer, vertical_edge_image):
        """Test that vertical edge produces horizontal dominant direction."""
        # Note: vertical line produces strong horizontal gradient (sobelx)
        result = analyzer.analyze(vertical_edge_image)
        assert result.dominant_direction == "horizontal"
    
    def test_dominant_direction_horizontal_edge(self, analyzer, horizontal_edge_image):
        """Test that horizontal edge produces vertical dominant direction."""
        # Note: horizontal line produces strong vertical gradient (sobely)
        result = analyzer.analyze(horizontal_edge_image)
        assert result.dominant_direction == "vertical"
    
    def test_canny_threshold_suggestion_type(self, analyzer, flat_image):
        """Test that Canny threshold suggestion returns tuple of two ints."""
        result = analyzer.analyze(flat_image)
        assert isinstance(result.canny_threshold_suggestion, tuple)
        assert len(result.canny_threshold_suggestion) == 2
        assert isinstance(result.canny_threshold_suggestion[0], int)
        assert isinstance(result.canny_threshold_suggestion[1], int)
    
    def test_canny_high_threshold_positive(self, analyzer, flat_image):
        """Test that high Canny threshold is positive."""
        result = analyzer.analyze(flat_image)
        assert result.canny_threshold_suggestion[1] > 0
    
    def test_is_suitable_for_caliper_strong_edge(self, analyzer, vertical_edge_image):
        """Test that strong edge image is suitable for caliper."""
        result = analyzer.analyze(vertical_edge_image)
        assert result.is_suitable_for_caliper is True
    
    def test_is_suitable_for_caliper_flat(self, analyzer, flat_image):
        """Test that flat image is not suitable for caliper."""
        result = analyzer.analyze(flat_image)
        assert result.is_suitable_for_caliper is False
    
    def test_caliper_direction_horizontal_dominant(self, analyzer, vertical_edge_image):
        """Test that horizontal dominant direction suggests vertical caliper."""
        result = analyzer.analyze(vertical_edge_image)
        # vertical edge → horizontal dominant → vertical caliper
        assert result.dominant_direction == "horizontal"
        assert result.caliper_direction_suggestion == "vertical"
    
    def test_caliper_direction_vertical_dominant(self, analyzer, horizontal_edge_image):
        """Test that vertical dominant direction suggests horizontal caliper."""
        result = analyzer.analyze(horizontal_edge_image)
        # horizontal edge → vertical dominant → horizontal caliper
        assert result.dominant_direction == "vertical"
        assert result.caliper_direction_suggestion == "horizontal"
    
    def test_get_edge_map_shape(self, analyzer, flat_image):
        """Test that edge map has same H×W shape as input."""
        edge_map = analyzer.get_edge_map(flat_image)
        assert edge_map.shape == flat_image.shape
    
    def test_get_edge_map_binary(self, analyzer, flat_image):
        """Test that all pixels in edge map are 0 or 255."""
        edge_map = analyzer.get_edge_map(flat_image)
        unique_values = np.unique(edge_map)
        assert all(val in [0, 255] for val in unique_values)
    
    def test_compare_ok_ng_keys(self, analyzer, flat_image):
        """Test that compare_ok_ng returns dict with all required keys."""
        ok_images = [flat_image]
        ng_images = [flat_image]
        result = analyzer.compare_ok_ng(ok_images, ng_images)
        
        expected_keys = {
            "ok_mean_strength", "ng_mean_strength",
            "ok_edge_density", "ng_edge_density",
            "strength_diff", "density_diff"
        }
        assert set(result.keys()) == expected_keys
    
    def test_compare_ok_ng_empty_ok_raises(self, analyzer, flat_image):
        """Test that empty OK images list raises RuntimeProcessingError."""
        ok_images = []
        ng_images = [flat_image]
        
        with pytest.raises(RuntimeProcessingError):
            analyzer.compare_ok_ng(ok_images, ng_images)
    
    def test_compare_ok_ng_empty_ng_raises(self, analyzer, flat_image):
        """Test that empty NG images list raises RuntimeProcessingError."""
        ok_images = [flat_image]
        ng_images = []
        
        with pytest.raises(RuntimeProcessingError):
            analyzer.compare_ok_ng(ok_images, ng_images)
    
    def test_horizontal_vertical_ratio_sum(self, analyzer, flat_image):
        """Test that horizontal and vertical ratios sum to 1.0."""
        result = analyzer.analyze(flat_image)
        ratio_sum = result.horizontal_ratio + result.vertical_ratio
        assert abs(ratio_sum - 1.0) < 1e-6
    
    def test_mixed_direction_detection(self, analyzer):
        """Test mixed direction detection for image with both horizontal and vertical edges."""
        # Create image with both horizontal and vertical edges
        img = np.zeros((100, 100), dtype=np.uint8)
        img[:, 30:35] = 255  # vertical edge
        img[30:35, :] = 255  # horizontal edge
        
        result = analyzer.analyze(img)
        # Should detect mixed or diagonal due to similar h/v energy
        assert result.dominant_direction in ["mixed", "diagonal"]
    
    def test_edge_analysis_result_attributes(self, analyzer, flat_image):
        """Test that all EdgeAnalysisResult attributes are present and correct types."""
        result = analyzer.analyze(flat_image)
        
        # Check all required attributes exist
        assert hasattr(result, 'mean_edge_strength')
        assert hasattr(result, 'max_edge_strength')
        assert hasattr(result, 'edge_density')
        assert hasattr(result, 'dominant_direction')
        assert hasattr(result, 'horizontal_ratio')
        assert hasattr(result, 'vertical_ratio')
        assert hasattr(result, 'canny_threshold_suggestion')
        assert hasattr(result, 'is_suitable_for_caliper')
        assert hasattr(result, 'caliper_direction_suggestion')
        
        # Check types
        assert isinstance(result.mean_edge_strength, float)
        assert isinstance(result.max_edge_strength, float)
        assert isinstance(result.edge_density, float)
        assert isinstance(result.dominant_direction, str)
        assert isinstance(result.horizontal_ratio, float)
        assert isinstance(result.vertical_ratio, float)
        assert isinstance(result.canny_threshold_suggestion, tuple)
        assert isinstance(result.is_suitable_for_caliper, bool)
        assert isinstance(result.caliper_direction_suggestion, str)
        
        # Check valid string values
        assert result.dominant_direction in ["horizontal", "vertical", "diagonal", "mixed"]
        assert result.caliper_direction_suggestion in ["horizontal", "vertical", "both"]
    
    def test_zero_edge_energy_handling(self, analyzer):
        """Test handling of image with zero edge energy."""
        # Create completely uniform image
        uniform_image = np.full((50, 50), 128, dtype=np.uint8)
        
        result = analyzer.analyze(uniform_image)
        
        # Should handle zero energy gracefully
        assert result.horizontal_ratio == 0.5
        assert result.vertical_ratio == 0.5
        assert result.dominant_direction == "mixed"