"""
Unit tests for noise analyzer.
"""

import numpy as np
import pytest

from config.constants import NOISE_LOW, NOISE_MEDIUM, NOISE_HIGH
from core.analyzers.noise_analyzer import NoiseAnalyzer, NoiseAnalysisResult
from core.exceptions import RuntimeProcessingError


class TestNoiseAnalyzer:
    """Test cases for NoiseAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = NoiseAnalyzer()
    
    def test_analyze_clean_image(self):
        """Test analysis of clean synthetic image."""
        # Create flat/uniform image (clean, low noise)
        image = np.ones((100, 100), dtype=np.uint8) * 128
        
        result = self.analyzer.analyze(image)
        
        assert result.noise_level == NOISE_LOW
        assert result.recommended_filter == "gaussian_blur"
        assert isinstance(result.laplacian_variance, float)
        assert isinstance(result.snr_db, float)
        assert isinstance(result.estimated_noise_std, float)
    
    def test_analyze_noisy_image(self):
        """Test analysis of noisy image."""
        # Create noisy image with strong Gaussian noise
        base = np.ones((100, 100), dtype=np.uint8) * 128
        np.random.seed(42)  # For reproducible results
        noise = np.random.normal(0, 50, base.shape)
        noisy = np.clip(base.astype(float) + noise, 0, 255).astype(np.uint8)
        
        result = self.analyzer.analyze(noisy)
        
        assert result.noise_level == NOISE_HIGH
        assert result.recommended_filter == "bilateral_filter"
    
    def test_analyze_grayscale_input(self):
        """Test grayscale 2D input handling."""
        # 2D grayscale image
        image = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        
        result = self.analyzer.analyze(image)
        
        # Should work without error
        assert isinstance(result, NoiseAnalysisResult)
        assert result.noise_level in [NOISE_LOW, NOISE_MEDIUM, NOISE_HIGH]
    
    def test_analyze_bgr_input(self):
        """Test BGR 3D input handling."""
        # 3D BGR image
        image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        
        result = self.analyzer.analyze(image)
        
        # Should convert to grayscale and work without error
        assert isinstance(result, NoiseAnalysisResult)
        assert result.noise_level in [NOISE_LOW, NOISE_MEDIUM, NOISE_HIGH]
    
    def test_laplacian_variance_positive(self):
        """Test that Laplacian variance is positive for any valid image."""
        # Create image with some variation
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        
        result = self.analyzer.analyze(image)
        
        assert result.laplacian_variance > 0
    
    def test_snr_db_type(self):
        """Test that SNR dB is float type."""
        image = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        
        result = self.analyzer.analyze(image)
        
        assert isinstance(result.snr_db, float)
    
    def test_snr_zero_noise(self):
        """Test SNR calculation for zero noise (flat image)."""
        # Flat image (all same value)
        image = np.full((100, 100), 128, dtype=np.uint8)
        
        result = self.analyzer.analyze(image)
        
        assert result.snr_db == 100.0
    
    def test_recommended_filter_low_noise(self):
        """Test filter recommendation for low noise."""
        # Create flat/uniform image (clean, low noise)
        image = np.ones((100, 100), dtype=np.uint8) * 128
        
        result = self.analyzer.analyze(image)
        
        if result.noise_level == NOISE_LOW:
            assert result.recommended_filter == "gaussian_blur"
    
    def test_recommended_filter_high_noise(self):
        """Test filter recommendation for high noise."""
        # Create very noisy image
        base = np.ones((100, 100), dtype=np.uint8) * 128
        np.random.seed(42)
        noise = np.random.normal(0, 60, base.shape)
        noisy = np.clip(base.astype(float) + noise, 0, 255).astype(np.uint8)
        
        result = self.analyzer.analyze(noisy)
        
        if result.noise_level == NOISE_HIGH:
            assert result.recommended_filter == "bilateral_filter"
    
    def test_compare_returns_list(self):
        """Test that compare returns list with correct length."""
        img1 = np.ones((50, 50), dtype=np.uint8) * 100
        img2 = np.ones((50, 50), dtype=np.uint8) * 150
        
        results = self.analyzer.compare([img1, img2])
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, NoiseAnalysisResult) for r in results)
    
    def test_compare_empty_raises(self):
        """Test that empty list raises RuntimeProcessingError."""
        with pytest.raises(RuntimeProcessingError, match="Images list is empty"):
            self.analyzer.compare([])
    
    def test_get_average_noise_level_majority(self):
        """Test average noise level with clear majority."""
        # Create results with majority LOW
        results = [
            NoiseAnalysisResult(0, 0, NOISE_LOW, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_LOW, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_HIGH, "", 0)
        ]
        
        average_level = self.analyzer.get_average_noise_level(results)
        
        assert average_level == NOISE_LOW
    
    def test_get_average_noise_level_tiebreak(self):
        """Test average noise level tie-breaking (prefer higher noise)."""
        # Create results with tie between LOW and HIGH
        results = [
            NoiseAnalysisResult(0, 0, NOISE_LOW, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_HIGH, "", 0)
        ]
        
        average_level = self.analyzer.get_average_noise_level(results)
        
        # Should prefer higher noise level (HIGH > MEDIUM > LOW)
        assert average_level == NOISE_HIGH
    
    def test_get_average_noise_level_empty_list(self):
        """Test average noise level with empty list."""
        average_level = self.analyzer.get_average_noise_level([])
        
        assert average_level == NOISE_LOW
    
    def test_is_suitable_for_caliper_low(self):
        """Test caliper suitability for low noise."""
        result = NoiseAnalysisResult(
            laplacian_variance=600.0,
            snr_db=50.0,
            noise_level=NOISE_LOW,
            recommended_filter="gaussian_blur",
            estimated_noise_std=5.0
        )
        
        assert self.analyzer.is_suitable_for_caliper(result) is True
    
    def test_is_suitable_for_caliper_medium(self):
        """Test caliper suitability for medium noise."""
        result = NoiseAnalysisResult(
            laplacian_variance=200.0,
            snr_db=30.0,
            noise_level=NOISE_MEDIUM,
            recommended_filter="median_blur",
            estimated_noise_std=15.0
        )
        
        assert self.analyzer.is_suitable_for_caliper(result) is True
    
    def test_is_suitable_for_caliper_high(self):
        """Test caliper suitability for high noise."""
        result = NoiseAnalysisResult(
            laplacian_variance=50.0,
            snr_db=10.0,
            noise_level=NOISE_HIGH,
            recommended_filter="bilateral_filter",
            estimated_noise_std=30.0
        )
        
        assert self.analyzer.is_suitable_for_caliper(result) is False
    
    def test_is_suitable_for_pattern_matching_low(self):
        """Test pattern matching suitability for low noise."""
        result = NoiseAnalysisResult(
            laplacian_variance=600.0,
            snr_db=50.0,
            noise_level=NOISE_LOW,
            recommended_filter="gaussian_blur",
            estimated_noise_std=5.0
        )
        
        assert self.analyzer.is_suitable_for_pattern_matching(result) is True
    
    def test_is_suitable_for_pattern_matching_medium(self):
        """Test pattern matching suitability for medium noise."""
        result = NoiseAnalysisResult(
            laplacian_variance=200.0,
            snr_db=30.0,
            noise_level=NOISE_MEDIUM,
            recommended_filter="median_blur",
            estimated_noise_std=15.0
        )
        
        assert self.analyzer.is_suitable_for_pattern_matching(result) is False
    
    def test_is_suitable_for_pattern_matching_high(self):
        """Test pattern matching suitability for high noise."""
        result = NoiseAnalysisResult(
            laplacian_variance=50.0,
            snr_db=10.0,
            noise_level=NOISE_HIGH,
            recommended_filter="bilateral_filter",
            estimated_noise_std=30.0
        )
        
        assert self.analyzer.is_suitable_for_pattern_matching(result) is False
    
    def test_noise_level_classification_thresholds(self):
        """Test noise level classification with controlled Laplacian variance."""
        # Test using synthetic data since Laplacian variance depends on image content
        # We test the boundary cases by checking the classification logic
        
        # Create images that should result in different noise levels
        # Flat image (should be LOW noise - clean/uniform)
        flat_image = np.ones((100, 100), dtype=np.uint8) * 128
        
        # Very noisy image (should be HIGH noise)
        base = np.ones((100, 100), dtype=np.uint8) * 128
        np.random.seed(42)
        noise = np.random.normal(0, 80, base.shape)
        very_noisy = np.clip(base.astype(float) + noise, 0, 255).astype(np.uint8)
        
        flat_result = self.analyzer.analyze(flat_image)
        noisy_result = self.analyzer.analyze(very_noisy)
        
        # Flat image should have low noise (clean/uniform)
        assert flat_result.noise_level == NOISE_LOW
        assert flat_result.laplacian_variance < 100
        
        # Very noisy image should have high noise
        assert noisy_result.noise_level == NOISE_HIGH
        assert noisy_result.laplacian_variance >= 500
    
    def test_estimated_noise_std_positive(self):
        """Test that estimated noise std is non-negative."""
        image = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        
        result = self.analyzer.analyze(image)
        
        assert result.estimated_noise_std >= 0
    
    def test_three_way_tie_break(self):
        """Test tie-breaking with all three noise levels."""
        # Create results with three-way tie
        results = [
            NoiseAnalysisResult(0, 0, NOISE_LOW, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_MEDIUM, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_HIGH, "", 0)
        ]
        
        average_level = self.analyzer.get_average_noise_level(results)
        
        # Should prefer highest noise level
        assert average_level == NOISE_HIGH
    
    def test_medium_high_tie_break(self):
        """Test tie-breaking between medium and high noise."""
        results = [
            NoiseAnalysisResult(0, 0, NOISE_MEDIUM, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_HIGH, "", 0)
        ]
        
        average_level = self.analyzer.get_average_noise_level(results)
        
        # Should prefer higher noise level
        assert average_level == NOISE_HIGH
    
    def test_low_medium_tie_break(self):
        """Test tie-breaking between low and medium noise."""
        results = [
            NoiseAnalysisResult(0, 0, NOISE_LOW, "", 0),
            NoiseAnalysisResult(0, 0, NOISE_MEDIUM, "", 0)
        ]
        
        average_level = self.analyzer.get_average_noise_level(results)
        
        # Should prefer higher noise level
        assert average_level == NOISE_MEDIUM