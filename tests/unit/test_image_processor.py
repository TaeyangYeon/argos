"""
Unit tests for the image processing utilities.

Tests image loading, preprocessing pipelines, and error handling
with both real images and synthetic test data.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from core.image_processor import ImageLoader, ImagePreprocessor
from core.exceptions import RuntimeProcessingError
from config.constants import NOISE_LOW, NOISE_MEDIUM, NOISE_HIGH


class TestImageLoader:
    """Test image loading and basic format conversions."""
    
    def test_load_valid_image(self):
        """Load tests/fixtures/sample_ok.png → returns np.ndarray, ndim == 3."""
        image_path = Path("tests/fixtures/sample_ok.png")
        image = ImageLoader.load(image_path)
        
        assert isinstance(image, np.ndarray)
        assert image.ndim == 3
        assert image.size > 0
    
    def test_load_grayscale(self):
        """Load as grayscale → ndim == 2."""
        image_path = Path("tests/fixtures/sample_ok.png")
        image = ImageLoader.load_grayscale(image_path)
        
        assert isinstance(image, np.ndarray)
        assert image.ndim == 2
        assert image.size > 0
    
    def test_load_nonexistent_raises(self):
        """Load "nonexistent.png" → RuntimeProcessingError."""
        with pytest.raises(RuntimeProcessingError):
            ImageLoader.load("nonexistent.png")
    
    def test_to_grayscale_from_bgr(self):
        """BGR input (ndim==3) → output ndim==2."""
        bgr_image = np.zeros((100, 100, 3), dtype=np.uint8)
        gray_image = ImageLoader.to_grayscale(bgr_image)
        
        assert gray_image.ndim == 2
        assert gray_image.shape == (100, 100)
    
    def test_to_grayscale_already_gray(self):
        """Grayscale input (ndim==2) → returns same ndim==2."""
        gray_image = np.zeros((100, 100), dtype=np.uint8)
        result = ImageLoader.to_grayscale(gray_image)
        
        assert result.ndim == 2
        assert result.shape == (100, 100)
        assert np.array_equal(result, gray_image)
    
    def test_to_bgr_from_gray(self):
        """Grayscale input → output ndim==3."""
        gray_image = np.zeros((100, 100), dtype=np.uint8)
        bgr_image = ImageLoader.to_bgr(gray_image)
        
        assert bgr_image.ndim == 3
        assert bgr_image.shape == (100, 100, 3)
    
    def test_to_bgr_already_bgr(self):
        """BGR input → returns same ndim==3."""
        bgr_image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = ImageLoader.to_bgr(bgr_image)
        
        assert result.ndim == 3
        assert result.shape == (100, 100, 3)
        assert np.array_equal(result, bgr_image)
    
    def test_validate_shape_none_raises(self):
        """None input → RuntimeProcessingError."""
        with pytest.raises(RuntimeProcessingError):
            ImageLoader.validate_shape(None)
    
    def test_validate_shape_empty_raises(self):
        """np.array([]) → RuntimeProcessingError."""
        empty_array = np.array([])
        with pytest.raises(RuntimeProcessingError):
            ImageLoader.validate_shape(empty_array)
    
    def test_validate_shape_invalid_dims_raises(self):
        """Invalid dimensions → RuntimeProcessingError."""
        # 1D array
        array_1d = np.zeros(100)
        with pytest.raises(RuntimeProcessingError):
            ImageLoader.validate_shape(array_1d)
        
        # 4D array
        array_4d = np.zeros((10, 10, 3, 2))
        with pytest.raises(RuntimeProcessingError):
            ImageLoader.validate_shape(array_4d)
    
    def test_validate_shape_valid_2d(self):
        """Valid 2D array → no error."""
        valid_2d = np.zeros((100, 100))
        ImageLoader.validate_shape(valid_2d)  # Should not raise
    
    def test_validate_shape_valid_3d(self):
        """Valid 3D array → no error."""
        valid_3d = np.zeros((100, 100, 3))
        ImageLoader.validate_shape(valid_3d)  # Should not raise


class TestImagePreprocessor:
    """Test image preprocessing pipeline and method chaining."""
    
    @pytest.fixture
    def sample_image_bgr(self):
        """Create a sample BGR image for testing."""
        return np.ones((100, 100, 3), dtype=np.uint8) * 128
    
    @pytest.fixture
    def sample_image_gray(self):
        """Create a sample grayscale image for testing."""
        return np.ones((100, 100), dtype=np.uint8) * 128
    
    def test_preprocessor_created(self, sample_image_bgr):
        """ImagePreprocessor(valid_image) → no error."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        assert preprocessor is not None
        assert np.array_equal(preprocessor._original, sample_image_bgr)
        assert np.array_equal(preprocessor._current, sample_image_bgr)
    
    def test_preprocessor_invalid_image_raises(self):
        """ImagePreprocessor(None) → RuntimeProcessingError."""
        with pytest.raises(RuntimeProcessingError):
            ImagePreprocessor(None)
    
    def test_gaussian_blur_applies(self, sample_image_bgr):
        """Apply gaussian_blur(3) → result shape unchanged."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = preprocessor.gaussian_blur(3).result()
        
        assert result.shape == sample_image_bgr.shape
        assert result.dtype == sample_image_bgr.dtype
    
    def test_median_blur_applies(self, sample_image_bgr):
        """Apply median_blur(3) → result shape unchanged."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = preprocessor.median_blur(3).result()
        
        assert result.shape == sample_image_bgr.shape
        assert result.dtype == sample_image_bgr.dtype
    
    def test_bilateral_filter_applies(self, sample_image_bgr):
        """Apply bilateral_filter() → result shape unchanged."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = preprocessor.bilateral_filter().result()
        
        assert result.shape == sample_image_bgr.shape
        assert result.dtype == sample_image_bgr.dtype
    
    def test_histogram_equalization_applies(self, sample_image_bgr):
        """Apply histogram_equalization() → ndim==2."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = preprocessor.histogram_equalization().result()
        
        assert result.ndim == 2
        assert result.dtype == sample_image_bgr.dtype
    
    def test_histogram_equalization_gray_input(self, sample_image_gray):
        """Apply histogram_equalization() on grayscale → ndim==2."""
        preprocessor = ImagePreprocessor(sample_image_gray)
        result = preprocessor.histogram_equalization().result()
        
        assert result.ndim == 2
        assert result.shape == sample_image_gray.shape
    
    def test_clahe_applies(self, sample_image_bgr):
        """Apply clahe() → ndim==2."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = preprocessor.clahe().result()
        
        assert result.ndim == 2
        assert result.dtype == sample_image_bgr.dtype
    
    def test_clahe_gray_input(self, sample_image_gray):
        """Apply clahe() on grayscale → ndim==2."""
        preprocessor = ImagePreprocessor(sample_image_gray)
        result = preprocessor.clahe().result()
        
        assert result.ndim == 2
        assert result.shape == sample_image_gray.shape
    
    def test_normalize_applies(self, sample_image_bgr):
        """Apply normalize() → pixel values in [0, 255]."""
        # Create image with varied pixel values
        test_image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        preprocessor = ImagePreprocessor(test_image)
        result = preprocessor.normalize().result()
        
        assert result.shape == test_image.shape
        assert result.min() >= 0
        assert result.max() <= 255
    
    def test_normalize_custom_range(self, sample_image_bgr):
        """Apply normalize(0, 100) → pixel values in [0, 100]."""
        test_image = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        preprocessor = ImagePreprocessor(test_image)
        result = preprocessor.normalize(0, 100).result()
        
        assert result.min() >= 0
        assert result.max() <= 100
    
    def test_method_chaining(self, sample_image_bgr):
        """preprocessor.gaussian_blur(3).normalize() → get_pipeline_steps() has 2 entries."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = preprocessor.gaussian_blur(3).normalize().result()
        
        steps = preprocessor.get_pipeline_steps()
        assert len(steps) == 2
        assert steps[0]["name"] == "gaussian_blur"
        assert steps[1]["name"] == "normalize"
    
    def test_complex_method_chaining(self, sample_image_bgr):
        """Test complex method chaining with multiple operations."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        result = (preprocessor
                  .gaussian_blur(5)
                  .median_blur(3)
                  .bilateral_filter()
                  .normalize()
                  .result())
        
        steps = preprocessor.get_pipeline_steps()
        assert len(steps) == 4
        assert steps[0]["name"] == "gaussian_blur"
        assert steps[1]["name"] == "median_blur" 
        assert steps[2]["name"] == "bilateral_filter"
        assert steps[3]["name"] == "normalize"
    
    def test_pipeline_steps_recorded(self, sample_image_bgr):
        """After gaussian_blur(5) → steps[0]["name"] == "gaussian_blur", steps[0]["kernel_size"] == 5."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        preprocessor.gaussian_blur(5)
        
        steps = preprocessor.get_pipeline_steps()
        assert len(steps) == 1
        assert steps[0]["name"] == "gaussian_blur"
        assert steps[0]["kernel_size"] == 5
        assert steps[0]["sigma"] == 0
    
    def test_bilateral_filter_steps_recorded(self, sample_image_bgr):
        """Test bilateral filter parameters are recorded correctly."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        preprocessor.bilateral_filter(d=15, sigma_color=80, sigma_space=80)
        
        steps = preprocessor.get_pipeline_steps()
        assert len(steps) == 1
        assert steps[0]["name"] == "bilateral_filter"
        assert steps[0]["d"] == 15
        assert steps[0]["sigma_color"] == 80
        assert steps[0]["sigma_space"] == 80
    
    def test_clahe_steps_recorded(self, sample_image_bgr):
        """Test CLAHE parameters are recorded correctly."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        preprocessor.clahe(clip_limit=3.0, tile_grid_size=(16, 16))
        
        steps = preprocessor.get_pipeline_steps()
        assert len(steps) == 1
        assert steps[0]["name"] == "clahe"
        assert steps[0]["clip_limit"] == 3.0
        assert steps[0]["tile_grid_size"] == (16, 16)
    
    def test_reset_clears_pipeline(self, sample_image_bgr):
        """Apply blur → reset() → get_pipeline_steps() is empty."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        preprocessor.gaussian_blur(3).normalize()
        
        # Verify steps were recorded
        assert len(preprocessor.get_pipeline_steps()) == 2
        
        # Reset and verify
        preprocessor.reset()
        assert len(preprocessor.get_pipeline_steps()) == 0
        assert np.array_equal(preprocessor.result(), sample_image_bgr)
    
    def test_even_kernel_raises_gaussian(self, sample_image_bgr):
        """gaussian_blur(4) → ValueError."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        with pytest.raises(ValueError, match="kernel_size must be odd, got 4"):
            preprocessor.gaussian_blur(4)
    
    def test_even_kernel_raises_median(self, sample_image_bgr):
        """median_blur(6) → ValueError."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        with pytest.raises(ValueError, match="kernel_size must be odd, got 6"):
            preprocessor.median_blur(6)
    
    def test_select_filter_low_noise(self):
        """select_filter_for_noise(NOISE_LOW) == "gaussian_blur"."""
        result = ImagePreprocessor.select_filter_for_noise(NOISE_LOW)
        assert result == "gaussian_blur"
    
    def test_select_filter_medium_noise(self):
        """select_filter_for_noise(NOISE_MEDIUM) == "median_blur"."""
        result = ImagePreprocessor.select_filter_for_noise(NOISE_MEDIUM)
        assert result == "median_blur"
    
    def test_select_filter_high_noise(self):
        """select_filter_for_noise(NOISE_HIGH) == "bilateral_filter"."""
        result = ImagePreprocessor.select_filter_for_noise(NOISE_HIGH)
        assert result == "bilateral_filter"
    
    def test_select_filter_unknown_noise(self):
        """select_filter_for_noise("unknown") → defaults to "gaussian_blur"."""
        result = ImagePreprocessor.select_filter_for_noise("unknown")
        assert result == "gaussian_blur"
    
    def test_get_pipeline_steps_copy(self, sample_image_bgr):
        """get_pipeline_steps() returns copy, not reference."""
        preprocessor = ImagePreprocessor(sample_image_bgr)
        preprocessor.gaussian_blur(3)
        
        steps = preprocessor.get_pipeline_steps()
        steps.append({"name": "fake_step"})
        
        # Original should be unchanged
        original_steps = preprocessor.get_pipeline_steps()
        assert len(original_steps) == 1
        assert original_steps[0]["name"] == "gaussian_blur"
    
    def test_original_image_unchanged(self, sample_image_bgr):
        """Original image should never be mutated."""
        original_copy = sample_image_bgr.copy()
        preprocessor = ImagePreprocessor(sample_image_bgr)
        
        # Apply multiple operations
        preprocessor.gaussian_blur(3).normalize().median_blur(5)
        
        # Original should be unchanged
        assert np.array_equal(preprocessor._original, original_copy)
        assert not np.array_equal(preprocessor._current, original_copy)


class TestImageLoaderWithRealImage:
    """Test ImageLoader with real image file."""
    
    def test_load_real_image_properties(self):
        """Test loading real image and verify properties."""
        image_path = Path("tests/fixtures/sample_ok.png")
        image = ImageLoader.load(image_path)
        
        assert image.ndim == 3
        assert image.shape[2] == 3  # BGR channels
        assert image.dtype == np.uint8
    
    def test_load_real_image_grayscale(self):
        """Test loading real image as grayscale."""
        image_path = Path("tests/fixtures/sample_ok.png")
        image = ImageLoader.load_grayscale(image_path)
        
        assert image.ndim == 2
        assert image.dtype == np.uint8


class TestImagePreprocessorWithRealImage:
    """Test ImagePreprocessor with real image file."""
    
    @pytest.fixture
    def real_image(self):
        """Load real image for testing."""
        return ImageLoader.load("tests/fixtures/sample_ok.png")
    
    def test_real_image_preprocessing_pipeline(self, real_image):
        """Test complete preprocessing pipeline on real image."""
        preprocessor = ImagePreprocessor(real_image)
        result = (preprocessor
                  .gaussian_blur(3)
                  .bilateral_filter(9, 75, 75)
                  .normalize(0, 255)
                  .result())
        
        assert result.shape == real_image.shape
        assert len(preprocessor.get_pipeline_steps()) == 3
    
    def test_real_image_grayscale_operations(self, real_image):
        """Test grayscale operations on real image."""
        preprocessor = ImagePreprocessor(real_image)
        result = (preprocessor
                  .histogram_equalization()
                  .clahe(2.0, (8, 8))
                  .result())
        
        assert result.ndim == 2  # Should be grayscale after hist eq
        assert len(preprocessor.get_pipeline_steps()) == 2