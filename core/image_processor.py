"""
Image processing utilities for the Argos vision algorithm design system.

This module provides image loading and preprocessing capabilities using OpenCV,
with comprehensive error handling and method chaining support for preprocessing pipelines.
"""

from pathlib import Path
from typing import Union

import cv2
import numpy as np

from core.exceptions import RuntimeProcessingError
from core.logger import get_logger
from config.constants import NOISE_LOW, NOISE_MEDIUM, NOISE_HIGH


class ImageLoader:
    """Static methods for loading and basic image format conversion."""
    
    @staticmethod
    def load(file_path: Union[str, Path]) -> np.ndarray:
        """
        Load image using cv2.imread().
        
        Args:
            file_path: Path to the image file
            
        Returns:
            BGR numpy array
            
        Raises:
            RuntimeProcessingError: If image cannot be loaded
        """
        logger = get_logger("image_processor")
        logger.debug(f"Loading image: {Path(file_path).name}")
        
        image = cv2.imread(str(file_path))
        if image is None:
            RuntimeProcessingError.raise_with_log(
                f"Failed to load image: {Path(file_path).name}",
                logger
            )
        
        return image
    
    @staticmethod
    def load_grayscale(file_path: Union[str, Path]) -> np.ndarray:
        """
        Load image as grayscale using cv2.IMREAD_GRAYSCALE.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Grayscale numpy array
            
        Raises:
            RuntimeProcessingError: If image cannot be loaded
        """
        logger = get_logger("image_processor")
        logger.debug(f"Loading image: {Path(file_path).name}")
        
        image = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            RuntimeProcessingError.raise_with_log(
                f"Failed to load image: {Path(file_path).name}",
                logger
            )
        
        return image
    
    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """
        Convert BGR image to grayscale.
        
        Args:
            image: Input image array
            
        Returns:
            Grayscale image array
        """
        if image.ndim == 2:
            # Already grayscale
            return image
        
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    @staticmethod
    def to_bgr(image: np.ndarray) -> np.ndarray:
        """
        Convert grayscale image to BGR.
        
        Args:
            image: Input image array
            
        Returns:
            BGR image array
        """
        if image.ndim == 3:
            # Already BGR
            return image
        
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    @staticmethod
    def validate_shape(image: np.ndarray) -> None:
        """
        Validate image shape and properties.
        
        Args:
            image: Input image array
            
        Raises:
            RuntimeProcessingError: If image is invalid
        """
        logger = get_logger("image_processor")
        
        # Check if image is None
        if image is None:
            RuntimeProcessingError.raise_with_log(
                "Image is None",
                logger
            )
        
        # Check if image is empty
        if image.size == 0:
            RuntimeProcessingError.raise_with_log(
                "Image is empty (size == 0)",
                logger
            )
        
        # Check if image has valid dimensions
        if image.ndim not in (2, 3):
            RuntimeProcessingError.raise_with_log(
                f"Invalid image dimensions: {image.ndim}. Expected 2 or 3.",
                logger
            )


class ImagePreprocessor:
    """Image preprocessing pipeline with method chaining support."""
    
    def __init__(self, image: np.ndarray):
        """
        Initialize preprocessor with input image.
        
        Args:
            image: Input image array
            
        Raises:
            RuntimeProcessingError: If image is invalid
        """
        ImageLoader.validate_shape(image)
        
        self._original = image
        self._current = image.copy()
        self._pipeline_steps = []
    
    def gaussian_blur(self, kernel_size: int = 3, sigma: float = 0) -> 'ImagePreprocessor':
        """
        Apply Gaussian blur filter.
        
        Args:
            kernel_size: Size of the Gaussian kernel (must be odd)
            sigma: Gaussian kernel standard deviation
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If kernel_size is even
        """
        if kernel_size % 2 == 0:
            raise ValueError(f"kernel_size must be odd, got {kernel_size}")
        
        self._current = cv2.GaussianBlur(self._current, (kernel_size, kernel_size), sigma)
        
        self._pipeline_steps.append({
            "name": "gaussian_blur",
            "kernel_size": kernel_size,
            "sigma": sigma
        })
        
        return self
    
    def median_blur(self, kernel_size: int = 3) -> 'ImagePreprocessor':
        """
        Apply median blur filter.
        
        Args:
            kernel_size: Size of the median filter kernel (must be odd)
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If kernel_size is even
        """
        if kernel_size % 2 == 0:
            raise ValueError(f"kernel_size must be odd, got {kernel_size}")
        
        self._current = cv2.medianBlur(self._current, kernel_size)
        
        self._pipeline_steps.append({
            "name": "median_blur",
            "kernel_size": kernel_size
        })
        
        return self
    
    def bilateral_filter(self, d: int = 9, sigma_color: float = 75, 
                        sigma_space: float = 75) -> 'ImagePreprocessor':
        """
        Apply bilateral filter for noise reduction while preserving edges.
        
        Args:
            d: Diameter of each pixel neighborhood
            sigma_color: Filter sigma in the color space
            sigma_space: Filter sigma in the coordinate space
            
        Returns:
            Self for method chaining
        """
        self._current = cv2.bilateralFilter(self._current, d, sigma_color, sigma_space)
        
        self._pipeline_steps.append({
            "name": "bilateral_filter",
            "d": d,
            "sigma_color": sigma_color,
            "sigma_space": sigma_space
        })
        
        return self
    
    def histogram_equalization(self) -> 'ImagePreprocessor':
        """
        Apply histogram equalization for contrast enhancement.
        
        Returns:
            Self for method chaining
        """
        # Convert to grayscale if needed
        if self._current.ndim == 3:
            self._current = ImageLoader.to_grayscale(self._current)
        
        self._current = cv2.equalizeHist(self._current)
        
        self._pipeline_steps.append({
            "name": "histogram_equalization"
        })
        
        return self
    
    def clahe(self, clip_limit: float = 2.0, 
              tile_grid_size: tuple = (8, 8)) -> 'ImagePreprocessor':
        """
        Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).
        
        Args:
            clip_limit: Threshold for contrast limiting
            tile_grid_size: Size of the grid for histogram equalization
            
        Returns:
            Self for method chaining
        """
        # Convert to grayscale if needed
        if self._current.ndim == 3:
            self._current = ImageLoader.to_grayscale(self._current)
        
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        self._current = clahe.apply(self._current)
        
        self._pipeline_steps.append({
            "name": "clahe",
            "clip_limit": clip_limit,
            "tile_grid_size": tile_grid_size
        })
        
        return self
    
    def normalize(self, alpha: float = 0, beta: float = 255) -> 'ImagePreprocessor':
        """
        Normalize image pixel values to specified range.
        
        Args:
            alpha: Lower bound of the normalization range
            beta: Upper bound of the normalization range
            
        Returns:
            Self for method chaining
        """
        self._current = cv2.normalize(self._current, None, alpha, beta, cv2.NORM_MINMAX)
        
        self._pipeline_steps.append({
            "name": "normalize",
            "alpha": alpha,
            "beta": beta
        })
        
        return self
    
    def result(self) -> np.ndarray:
        """
        Get the final processed image.
        
        Returns:
            Processed image array
        """
        return self._current
    
    def get_pipeline_steps(self) -> list[dict]:
        """
        Get copy of the pipeline steps.
        
        Returns:
            List of dictionaries describing applied processing steps
        """
        return self._pipeline_steps.copy()
    
    def reset(self) -> 'ImagePreprocessor':
        """
        Reset to original image and clear pipeline.
        
        Returns:
            Self for method chaining
        """
        self._current = self._original.copy()
        self._pipeline_steps.clear()
        
        return self
    
    @staticmethod
    def select_filter_for_noise(noise_level: str) -> str:
        """
        Select recommended filter based on noise level.
        
        Args:
            noise_level: Noise level (NOISE_LOW, NOISE_MEDIUM, or NOISE_HIGH)
            
        Returns:
            Recommended filter name
        """
        if noise_level == NOISE_LOW:
            return "gaussian_blur"
        elif noise_level == NOISE_MEDIUM:
            return "median_blur"
        elif noise_level == NOISE_HIGH:
            return "bilateral_filter"
        else:
            # Default to gaussian blur for unknown noise levels
            return "gaussian_blur"