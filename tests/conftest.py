"""
Shared test fixtures for the Argos test suite.

This module provides common fixtures and helper functions used across
all test modules, including mock data and component setup utilities.
"""

import pytest
import numpy as np
from datetime import datetime

from core.image_store import ImageMeta, ImageType


@pytest.fixture
def make_image_meta():
    """
    Factory fixture for creating ImageMeta instances with synthetic data.
    
    Returns:
        Function that creates ImageMeta with given parameters
    """
    def _make_meta(
        image_type: ImageType = ImageType.ALIGN_OK,
        filename: str = "test_image.png",
        width: int = 640,
        height: int = 480,
        file_size_bytes: int = 102400,
        image_id: str = None
    ) -> ImageMeta:
        """
        Create a mock ImageMeta with synthetic thumbnail.
        
        Args:
            image_type: Type of image
            filename: Image filename
            width: Image width in pixels
            height: Image height in pixels
            file_size_bytes: File size in bytes
            image_id: Custom image ID, or auto-generated if None
            
        Returns:
            ImageMeta instance with synthetic thumbnail
        """
        if image_id is None:
            image_id = f"test_{image_type.value}_{filename}"
            
        # Create a synthetic thumbnail (64x64 RGB)
        thumbnail = np.zeros((64, 64, 3), dtype=np.uint8)
        
        # Add some basic color based on type for visual distinction
        if image_type == ImageType.ALIGN_OK:
            thumbnail[:, :, 2] = 100  # Blue tint
        elif image_type == ImageType.INSPECTION_OK:
            thumbnail[:, :, 1] = 100  # Green tint
        elif image_type == ImageType.INSPECTION_NG:
            thumbnail[:, :, 0] = 100  # Red tint (BGR format)
            
        # Add some pattern to make it visually recognizable
        thumbnail[10:54, 10:54] = 255  # White square in center
        
        return ImageMeta(
            id=image_id,
            file_path=f"/test/path/{filename}",
            image_type=image_type,
            width=width,
            height=height,
            file_size_bytes=file_size_bytes,
            added_at=datetime.now().isoformat(),
            thumbnail=thumbnail
        )
    
    return _make_meta


@pytest.fixture
def sample_image_metas(make_image_meta):
    """
    Fixture providing a list of sample ImageMeta instances for testing.
    
    Returns:
        List of ImageMeta instances with different types
    """
    return [
        make_image_meta(ImageType.ALIGN_OK, "align_01.png", image_id="align_01"),
        make_image_meta(ImageType.ALIGN_OK, "align_02.jpg", image_id="align_02"),
        make_image_meta(ImageType.INSPECTION_OK, "ok_01.png", image_id="ok_01"),
        make_image_meta(ImageType.INSPECTION_OK, "ok_02.bmp", image_id="ok_02"),
        make_image_meta(ImageType.INSPECTION_NG, "ng_01.png", image_id="ng_01"),
    ]


@pytest.fixture
def grayscale_image_meta(make_image_meta):
    """
    Fixture providing an ImageMeta with grayscale thumbnail for testing.
    
    Returns:
        ImageMeta with grayscale thumbnail
    """
    meta = make_image_meta(ImageType.ALIGN_OK, "grayscale.png", image_id="grayscale_01")
    
    # Replace thumbnail with grayscale (2D array)
    meta.thumbnail = np.full((64, 64), 128, dtype=np.uint8)
    
    return meta