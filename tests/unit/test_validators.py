"""
Unit tests for the input validation layer.

Tests all validation functionality including image validation, ROI validation,
and sample validation using synthetic test data and fixtures.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from core.exceptions import InputValidationError
from core.models import ROIConfig
from core.validators import ImageValidator, ROIValidator, SampleValidator
from config.constants import MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT, NG_MINIMUM_RECOMMENDED


class TestImageValidator:
    """Tests for image validation functionality."""
    
    def test_validate_format_supported(self):
        """Test that supported formats pass validation."""
        supported_files = [
            "test.png", "test.jpg", "test.jpeg", 
            "test.bmp", "test.tiff", "test.tif"
        ]
        
        for filename in supported_files:
            # Should not raise exception
            ImageValidator.validate_format(filename)
    
    def test_validate_format_unsupported(self):
        """Test that unsupported formats raise InputValidationError."""
        unsupported_files = ["test.gif", "test.webp", "test.pdf", "test.svg"]
        
        for filename in unsupported_files:
            with pytest.raises(InputValidationError, match="Unsupported format"):
                ImageValidator.validate_format(filename)
    
    def test_validate_file_exists_missing(self, tmp_path):
        """Test that missing files raise InputValidationError."""
        nonexistent_file = tmp_path / "nonexistent.png"
        
        with pytest.raises(InputValidationError, match="File does not exist"):
            ImageValidator.validate_file_exists(nonexistent_file)
    
    def test_validate_file_exists_present(self, tmp_path):
        """Test that existing files pass validation."""
        existing_file = tmp_path / "existing.png"
        existing_file.write_text("dummy content")
        
        # Should not raise exception
        ImageValidator.validate_file_exists(existing_file)
    
    def test_validate_resolution_too_small(self):
        """Test that images smaller than minimum resolution are rejected."""
        small_image = np.zeros((32, 32, 3), dtype=np.uint8)  # 32x32 is too small
        
        with pytest.raises(InputValidationError, match="Image too small"):
            ImageValidator.validate_resolution(small_image)
    
    def test_validate_resolution_minimum_pass(self):
        """Test that minimum resolution images pass validation."""
        min_image = np.zeros((MIN_IMAGE_HEIGHT, MIN_IMAGE_WIDTH, 3), dtype=np.uint8)
        
        # Should not raise exception
        ImageValidator.validate_resolution(min_image)
    
    def test_validate_resolution_larger_pass(self):
        """Test that larger images pass validation."""
        large_image = np.zeros((200, 300, 3), dtype=np.uint8)
        
        # Should not raise exception
        ImageValidator.validate_resolution(large_image)
    
    def test_validate_not_corrupted_valid(self):
        """Test that valid image files pass corruption check."""
        # Use the fixture we created
        sample_file = Path("tests/fixtures/sample_ok.png")
        
        # Should not raise exception
        ImageValidator.validate_not_corrupted(sample_file)
    
    def test_validate_not_corrupted_invalid(self, tmp_path):
        """Test that corrupted files raise InputValidationError."""
        corrupted_file = tmp_path / "corrupted.png"
        
        # Write random bytes that don't form a valid image
        corrupted_file.write_bytes(b"this is not a valid image file content")
        
        with pytest.raises(InputValidationError, match="File appears corrupted"):
            ImageValidator.validate_not_corrupted(corrupted_file)
    
    def test_validate_image_full_pipeline(self, tmp_path):
        """Test complete image validation pipeline."""
        # Create a valid test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        test_image[10:90, 10:90] = [100, 150, 200]
        
        test_file = tmp_path / "valid_test.png"
        cv2.imwrite(str(test_file), test_image)
        
        # Should return the loaded image
        result = ImageValidator.validate_image(test_file)
        
        assert isinstance(result, np.ndarray)
        assert result.shape[:2] == (100, 100)
    
    def test_validate_image_fails_on_missing_file(self, tmp_path):
        """Test that image validation fails on missing file."""
        missing_file = tmp_path / "missing.png"
        
        with pytest.raises(InputValidationError, match="File does not exist"):
            ImageValidator.validate_image(missing_file)
    
    def test_validate_image_fails_on_unsupported_format(self, tmp_path):
        """Test that image validation fails on unsupported format."""
        unsupported_file = tmp_path / "test.gif"
        unsupported_file.write_text("dummy")
        
        with pytest.raises(InputValidationError, match="Unsupported format"):
            ImageValidator.validate_image(unsupported_file)
    
    def test_validate_image_fails_on_corrupted_file(self, tmp_path):
        """Test that image validation fails on corrupted file."""
        corrupted_file = tmp_path / "corrupted.png"
        corrupted_file.write_bytes(b"corrupted image data")
        
        with pytest.raises(InputValidationError, match="File appears corrupted"):
            ImageValidator.validate_image(corrupted_file)


class TestROIValidator:
    """Tests for ROI validation functionality."""
    
    def test_validate_within_bounds_valid(self):
        """Test that ROI within image bounds passes validation."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=10, y=10, width=50, height=50)
        
        # Should not raise exception
        ROIValidator.validate_within_bounds(roi, image)
    
    def test_validate_within_bounds_exceeds_right(self):
        """Test that ROI exceeding right boundary raises InputValidationError."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=80, y=10, width=30, height=50)  # Goes beyond width
        
        with pytest.raises(InputValidationError, match="ROI extends outside image boundaries"):
            ROIValidator.validate_within_bounds(roi, image)
    
    def test_validate_within_bounds_exceeds_bottom(self):
        """Test that ROI exceeding bottom boundary raises InputValidationError."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=10, y=80, width=50, height=30)  # Goes beyond height
        
        with pytest.raises(InputValidationError, match="ROI extends outside image boundaries"):
            ROIValidator.validate_within_bounds(roi, image)
    
    def test_validate_within_bounds_negative_coordinates(self):
        """Test that negative ROI coordinates raise InputValidationError."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=-5, y=10, width=50, height=50)
        
        with pytest.raises(InputValidationError, match="ROI extends outside image boundaries"):
            ROIValidator.validate_within_bounds(roi, image)
    
    def test_validate_non_zero_size_zero_width(self):
        """Test that zero width raises InputValidationError."""
        roi = ROIConfig(x=10, y=10, width=0, height=50)
        
        with pytest.raises(InputValidationError, match="ROI width and height must be greater than zero"):
            ROIValidator.validate_non_zero_size(roi)
    
    def test_validate_non_zero_size_zero_height(self):
        """Test that zero height raises InputValidationError."""
        roi = ROIConfig(x=10, y=10, width=50, height=0)
        
        with pytest.raises(InputValidationError, match="ROI width and height must be greater than zero"):
            ROIValidator.validate_non_zero_size(roi)
    
    def test_validate_non_zero_size_negative_dimensions(self):
        """Test that negative dimensions raise InputValidationError."""
        roi = ROIConfig(x=10, y=10, width=-10, height=50)
        
        with pytest.raises(InputValidationError, match="ROI width and height must be greater than zero"):
            ROIValidator.validate_non_zero_size(roi)
    
    def test_validate_non_zero_size_valid(self):
        """Test that positive dimensions pass validation."""
        roi = ROIConfig(x=10, y=10, width=50, height=50)
        
        # Should not raise exception
        ROIValidator.validate_non_zero_size(roi)
    
    def test_validate_minimum_area_too_small(self):
        """Test that ROI area below minimum raises InputValidationError."""
        image = np.zeros((1000, 1000, 3), dtype=np.uint8)  # Large image
        roi = ROIConfig(x=10, y=10, width=5, height=5)  # Very small ROI (25 pixels out of 1M)
        
        with pytest.raises(InputValidationError, match="ROI area too small"):
            ROIValidator.validate_minimum_area(roi, image)
    
    def test_validate_minimum_area_sufficient(self):
        """Test that ROI area meeting minimum requirement passes validation."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)  # 10,000 pixels
        roi = ROIConfig(x=10, y=10, width=20, height=20)  # 400 pixels = 4% of image
        
        # Should not raise exception (4% > 1% minimum)
        ROIValidator.validate_minimum_area(roi, image)
    
    def test_validate_minimum_area_exactly_minimum(self):
        """Test that ROI area exactly at minimum passes validation."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)  # 10,000 pixels
        roi = ROIConfig(x=10, y=10, width=10, height=10)  # 100 pixels = 1% of image
        
        # Should not raise exception (exactly 1% minimum)
        ROIValidator.validate_minimum_area(roi, image)
    
    def test_validate_roi_full_pipeline(self):
        """Test complete ROI validation pipeline."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=10, y=10, width=50, height=50)  # Valid ROI
        
        # Should not raise exception
        ROIValidator.validate_roi(roi, image)
    
    def test_validate_roi_fails_on_zero_size(self):
        """Test that ROI validation fails on zero size."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=10, y=10, width=0, height=50)
        
        with pytest.raises(InputValidationError, match="ROI width and height must be greater than zero"):
            ROIValidator.validate_roi(roi, image)
    
    def test_validate_roi_fails_on_out_of_bounds(self):
        """Test that ROI validation fails when out of bounds."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        roi = ROIConfig(x=10, y=10, width=100, height=50)  # Width extends beyond image
        
        with pytest.raises(InputValidationError, match="ROI extends outside image boundaries"):
            ROIValidator.validate_roi(roi, image)


class TestSampleValidator:
    """Tests for sample validation functionality."""
    
    def test_validate_ng_not_empty_zero(self):
        """Test that zero NG samples raise InputValidationError."""
        with pytest.raises(InputValidationError, match="⚠️ NG 이미지가 필요합니다"):
            SampleValidator.validate_ng_not_empty(0)
    
    def test_validate_ng_not_empty_one(self):
        """Test that one NG sample passes validation."""
        # Should not raise exception
        SampleValidator.validate_ng_not_empty(1)
    
    def test_validate_ng_not_empty_multiple(self):
        """Test that multiple NG samples pass validation."""
        # Should not raise exception
        SampleValidator.validate_ng_not_empty(5)
    
    def test_validate_ng_minimum_recommended_below(self):
        """Test that below-recommended NG count returns warning string."""
        result = SampleValidator.validate_ng_minimum_recommended(1)
        
        assert result is not None
        assert "샘플 부족" in result
        assert "정확도 신뢰도 낮음" in result
        assert "현재 1장" in result
        assert f"권장 {NG_MINIMUM_RECOMMENDED}장" in result
    
    def test_validate_ng_minimum_recommended_exactly_minimum(self):
        """Test that exactly minimum recommended count returns None."""
        result = SampleValidator.validate_ng_minimum_recommended(NG_MINIMUM_RECOMMENDED)
        
        assert result is None
    
    def test_validate_ng_minimum_recommended_sufficient(self):
        """Test that above-recommended NG count returns None."""
        result = SampleValidator.validate_ng_minimum_recommended(NG_MINIMUM_RECOMMENDED + 2)
        
        assert result is None
    
    def test_validate_ok_not_empty_zero(self):
        """Test that zero OK samples raise InputValidationError."""
        with pytest.raises(InputValidationError, match="OK 이미지가 최소 1장 필요합니다"):
            SampleValidator.validate_ok_not_empty(0)
    
    def test_validate_ok_not_empty_one(self):
        """Test that one OK sample passes validation."""
        # Should not raise exception
        SampleValidator.validate_ok_not_empty(1)
    
    def test_validate_ok_not_empty_multiple(self):
        """Test that multiple OK samples pass validation."""
        # Should not raise exception
        SampleValidator.validate_ok_not_empty(10)