"""
Unit tests for histogram analyzer.
"""

import numpy as np
import pytest

from core.analyzers.histogram_analyzer import HistogramAnalyzer, HistogramAnalysisResult
from core.exceptions import RuntimeProcessingError


class TestHistogramAnalyzer:
    """Test cases for HistogramAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = HistogramAnalyzer()
    
    def test_analyze_single_basic(self):
        """Test basic single image analysis."""
        # Create synthetic uniform gray image
        image = np.full((100, 100), 128, dtype=np.uint8)
        
        result = self.analyzer.analyze_single(image)
        
        assert result.mean_gray == pytest.approx(128.0, abs=1e-6)
        assert result.std_gray == pytest.approx(0.0, abs=1e-6)
        assert result.min_gray == 128
        assert result.max_gray == 128
        assert result.dynamic_range == 0
    
    def test_analyze_single_dynamic_range(self):
        """Test dynamic range calculation."""
        # Create image with full range (0 to 255)
        image = np.zeros((100, 100), dtype=np.uint8)
        image[:50] = 0    # Top half black
        image[50:] = 255  # Bottom half white
        
        result = self.analyzer.analyze_single(image)
        
        assert result.min_gray == 0
        assert result.max_gray == 255
        assert result.dynamic_range == 255
    
    def test_analyze_single_grayscale_input(self):
        """Test grayscale 2D input handling."""
        # 2D grayscale image
        image = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        
        result = self.analyzer.analyze_single(image)
        
        # Should work without error
        assert isinstance(result, HistogramAnalysisResult)
        assert 0 <= result.mean_gray <= 255
        assert result.std_gray >= 0
    
    def test_analyze_single_bgr_input(self):
        """Test BGR 3D input handling."""
        # 3D BGR image
        image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        
        result = self.analyzer.analyze_single(image)
        
        # Should convert to grayscale and work without error
        assert isinstance(result, HistogramAnalysisResult)
        assert 0 <= result.mean_gray <= 255
        assert result.std_gray >= 0
    
    def test_distribution_type_bimodal(self):
        """Test bimodal distribution detection."""
        # Create image with two distinct gray levels
        image = np.zeros((100, 100), dtype=np.uint8)
        image[:50] = 50   # First peak at 50
        image[50:] = 200  # Second peak at 200
        
        result = self.analyzer.analyze_single(image)
        
        assert result.distribution_type == "bimodal"
        assert result.peak_count >= 2
    
    def test_distribution_type_unimodal(self):
        """Test unimodal distribution detection."""
        # Create uniform gray image (single peak)
        image = np.full((100, 100), 128, dtype=np.uint8)
        
        result = self.analyzer.analyze_single(image)
        
        assert result.distribution_type == "unimodal"
        assert result.peak_count == 1
    
    def test_analyze_separation_calculates_score(self):
        """Test separation score calculation."""
        # Create OK images (bright)
        ok_images = [np.full((50, 50), 200, dtype=np.uint8)]
        
        # Create NG images (dark)
        ng_images = [np.full((50, 50), 50, dtype=np.uint8)]
        
        result = self.analyzer.analyze_separation(ok_images, ng_images)
        
        assert result.ok_mean == pytest.approx(200.0, abs=1e-6)
        assert result.ng_mean == pytest.approx(50.0, abs=1e-6)
        # separation_score = abs(200 - 50) / 255 * 100 = 58.82
        assert result.separation_score == pytest.approx(58.82, abs=0.01)
    
    def test_analyze_separation_empty_ok_raises(self):
        """Test error when OK images list is empty."""
        ok_images = []
        ng_images = [np.full((50, 50), 50, dtype=np.uint8)]
        
        with pytest.raises(RuntimeProcessingError, match="OK images list is empty"):
            self.analyzer.analyze_separation(ok_images, ng_images)
    
    def test_analyze_separation_empty_ng_raises(self):
        """Test error when NG images list is empty."""
        ok_images = [np.full((50, 50), 200, dtype=np.uint8)]
        ng_images = []
        
        with pytest.raises(RuntimeProcessingError, match="NG images list is empty"):
            self.analyzer.analyze_separation(ok_images, ng_images)
    
    def test_get_histogram_data_shape(self):
        """Test histogram data shape."""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        
        bin_edges, hist_values = self.analyzer.get_histogram_data(image)
        
        assert bin_edges.shape == (256,)
        assert hist_values.shape == (256,)
    
    def test_get_histogram_data_normalized(self):
        """Test histogram normalization."""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        
        bin_edges, hist_values = self.analyzer.get_histogram_data(image)
        
        assert np.max(hist_values) <= 1.0
        assert np.min(hist_values) >= 0.0
    
    def test_is_sufficient_contrast_true(self):
        """Test sufficient contrast detection."""
        # Create result with high dynamic range
        result = HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=50.0,
            min_gray=0,
            max_gray=255,
            dynamic_range=255,
            peak_count=1,
            distribution_type="unimodal"
        )
        
        assert self.analyzer.is_sufficient_contrast(result) is True
        assert self.analyzer.is_sufficient_contrast(result, min_dynamic_range=100) is True
    
    def test_is_sufficient_contrast_false(self):
        """Test insufficient contrast detection."""
        # Create result with low dynamic range
        result = HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=10.0,
            min_gray=120,
            max_gray=130,
            dynamic_range=10,
            peak_count=1,
            distribution_type="unimodal"
        )
        
        assert self.analyzer.is_sufficient_contrast(result) is False
        assert self.analyzer.is_sufficient_contrast(result, min_dynamic_range=30) is False
    
    def test_suggest_preprocessing_low_contrast(self):
        """Test preprocessing suggestions for low contrast."""
        result = HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=30.0,
            min_gray=120,
            max_gray=140,
            dynamic_range=20,  # Low dynamic range
            peak_count=1,
            distribution_type="unimodal"
        )
        
        suggestions = self.analyzer.suggest_preprocessing(result)
        
        assert "histogram_equalization" in suggestions
    
    def test_suggest_preprocessing_good_image(self):
        """Test no suggestions for good image."""
        result = HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=50.0,
            min_gray=0,
            max_gray=255,
            dynamic_range=255,  # Good dynamic range
            peak_count=1,
            distribution_type="unimodal"
        )
        
        suggestions = self.analyzer.suggest_preprocessing(result)
        
        assert len(suggestions) == 0
    
    def test_suggest_preprocessing_too_dark(self):
        """Test preprocessing suggestions for too dark image."""
        result = HistogramAnalysisResult(
            mean_gray=30.0,  # Too dark
            std_gray=50.0,
            min_gray=0,
            max_gray=100,
            dynamic_range=100,
            peak_count=1,
            distribution_type="unimodal"
        )
        
        suggestions = self.analyzer.suggest_preprocessing(result)
        
        assert "normalize" in suggestions
    
    def test_suggest_preprocessing_too_bright(self):
        """Test preprocessing suggestions for too bright image."""
        result = HistogramAnalysisResult(
            mean_gray=220.0,  # Too bright
            std_gray=50.0,
            min_gray=150,
            max_gray=255,
            dynamic_range=105,
            peak_count=1,
            distribution_type="unimodal"
        )
        
        suggestions = self.analyzer.suggest_preprocessing(result)
        
        assert "normalize" in suggestions
    
    def test_suggest_preprocessing_low_std(self):
        """Test preprocessing suggestions for low standard deviation."""
        result = HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=15.0,  # Low std
            min_gray=100,
            max_gray=150,
            dynamic_range=50,
            peak_count=1,
            distribution_type="unimodal"
        )
        
        suggestions = self.analyzer.suggest_preprocessing(result)
        
        assert "clahe" in suggestions
    
    def test_suggest_preprocessing_flat_distribution(self):
        """Test preprocessing suggestions for flat distribution."""
        result = HistogramAnalysisResult(
            mean_gray=128.0,
            std_gray=30.0,
            min_gray=0,
            max_gray=255,
            dynamic_range=255,
            peak_count=0,
            distribution_type="flat"  # Flat distribution
        )
        
        suggestions = self.analyzer.suggest_preprocessing(result)
        
        assert "normalize" in suggestions
    
    def test_bin_edges_correct_range(self):
        """Test bin edges are in correct range 0-255."""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        
        bin_edges, _ = self.analyzer.get_histogram_data(image)
        
        assert bin_edges[0] == 0
        assert bin_edges[-1] == 255
        assert len(bin_edges) == 256
    
    def test_empty_image_histogram(self):
        """Test histogram calculation for empty histogram."""
        # Create image with single value
        image = np.full((10, 10), 128, dtype=np.uint8)
        
        bin_edges, hist_values = self.analyzer.get_histogram_data(image)
        
        # Should handle normalization correctly
        assert len(hist_values) == 256
        assert np.max(hist_values) <= 1.0
    
    def test_multiple_ok_ng_images_separation(self):
        """Test separation analysis with multiple images."""
        # Multiple OK images
        ok_images = [
            np.full((50, 50), 180, dtype=np.uint8),
            np.full((50, 50), 200, dtype=np.uint8),
            np.full((50, 50), 220, dtype=np.uint8)
        ]
        
        # Multiple NG images  
        ng_images = [
            np.full((50, 50), 40, dtype=np.uint8),
            np.full((50, 50), 60, dtype=np.uint8),
            np.full((50, 50), 80, dtype=np.uint8)
        ]
        
        result = self.analyzer.analyze_separation(ok_images, ng_images)
        
        # Should average the means
        assert result.ok_mean == pytest.approx(200.0, abs=1e-6)  # (180+200+220)/3
        assert result.ng_mean == pytest.approx(60.0, abs=1e-6)   # (40+60+80)/3
        # separation_score = abs(200 - 60) / 255 * 100 = 54.90
        assert result.separation_score == pytest.approx(54.90, abs=0.01)