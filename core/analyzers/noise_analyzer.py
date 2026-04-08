"""
Noise level analysis for image quality assessment.

This module provides noise analysis capabilities for quantitative 
image assessment including Laplacian variance, SNR measurement,
and noise level classification for algorithm selection.
"""

from collections import Counter
from dataclasses import dataclass

import cv2
import numpy as np

from config.constants import NOISE_LOW, NOISE_MEDIUM, NOISE_HIGH
from core.exceptions import RuntimeProcessingError
from core.image_processor import ImageLoader
from core.logger import get_logger


@dataclass
class NoiseAnalysisResult:
    """Result of noise analysis."""
    laplacian_variance: float      # primary noise metric
    snr_db: float                 # Signal-to-Noise Ratio in decibels
    noise_level: str              # NOISE_LOW | NOISE_MEDIUM | NOISE_HIGH
    recommended_filter: str       # "gaussian_blur" | "median_blur" | "bilateral_filter"
    estimated_noise_std: float    # estimated standard deviation of noise


class NoiseAnalyzer:
    """Analyzer for noise level and signal-to-noise ratio."""
    
    def __init__(self):
        """Initialize noise analyzer."""
        self._logger = get_logger("noise_analyzer")
    
    def analyze(self, image: np.ndarray) -> NoiseAnalysisResult:
        """
        Analyze noise level and signal-to-noise ratio.
        
        Args:
            image: Input image (will be converted to grayscale)
            
        Returns:
            NoiseAnalysisResult with calculated noise metrics
        """
        # Convert to grayscale if needed
        gray = ImageLoader.to_grayscale(image)
        
        # 1. Calculate Laplacian variance
        kernel = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_variance = float(kernel.var())
        
        # 2. Estimate noise standard deviation using MAD method
        H = np.array([[1, -2, 1], 
                      [-2, 4, -2], 
                      [1, -2, 1]])
        sigma = cv2.filter2D(gray.astype(float), -1, H)
        estimated_noise_std = float(np.sqrt(np.pi / 2) * np.mean(np.abs(sigma)) / 6.0)
        
        # 3. Calculate SNR in dB
        signal_power = np.mean(gray.astype(float) ** 2)
        noise_power = estimated_noise_std ** 2
        if noise_power == 0:
            snr_db = 100.0
        else:
            snr_db = float(10 * np.log10(signal_power / noise_power))
        
        # 4. Classify noise level based on Laplacian variance
        # Low variance = flat/uniform = clean (NOISE_LOW)
        # High variance = noisy/textured = noisy (NOISE_HIGH)
        if laplacian_variance < 100:
            noise_level = NOISE_LOW
        elif laplacian_variance < 500:
            noise_level = NOISE_MEDIUM
        else:
            noise_level = NOISE_HIGH
        
        # 5. Recommend appropriate filter
        if noise_level == NOISE_LOW:
            recommended_filter = "gaussian_blur"
        elif noise_level == NOISE_MEDIUM:
            recommended_filter = "median_blur"
        else:  # NOISE_HIGH
            recommended_filter = "bilateral_filter"
        
        return NoiseAnalysisResult(
            laplacian_variance=laplacian_variance,
            snr_db=snr_db,
            noise_level=noise_level,
            recommended_filter=recommended_filter,
            estimated_noise_std=estimated_noise_std
        )
    
    def compare(self, images: list[np.ndarray]) -> list[NoiseAnalysisResult]:
        """
        Analyze noise level for multiple images.
        
        Args:
            images: List of images to analyze
            
        Returns:
            List of NoiseAnalysisResult for each image
            
        Raises:
            RuntimeProcessingError: If images list is empty
        """
        if not images:
            RuntimeProcessingError.raise_with_log(
                "Images list is empty",
                self._logger
            )
        
        results = []
        for image in images:
            result = self.analyze(image)
            results.append(result)
        
        return results
    
    def get_average_noise_level(self, results: list[NoiseAnalysisResult]) -> str:
        """
        Get the most common noise level among results.
        
        Args:
            results: List of noise analysis results
            
        Returns:
            Most common noise level (with tie-break: HIGH > MEDIUM > LOW)
        """
        if not results:
            return NOISE_LOW
        
        # Count noise levels
        noise_levels = [result.noise_level for result in results]
        counter = Counter(noise_levels)
        
        # Find maximum count
        max_count = max(counter.values())
        
        # Get all noise levels with maximum count
        tied_levels = [level for level, count in counter.items() if count == max_count]
        
        # Tie-break: prefer higher noise level (HIGH > MEDIUM > LOW)
        if NOISE_HIGH in tied_levels:
            return NOISE_HIGH
        elif NOISE_MEDIUM in tied_levels:
            return NOISE_MEDIUM
        else:
            return NOISE_LOW
    
    def is_suitable_for_caliper(self, result: NoiseAnalysisResult) -> bool:
        """
        Check if image is suitable for caliper-based analysis.
        
        Args:
            result: Noise analysis result
            
        Returns:
            True if noise level is LOW or MEDIUM
        """
        return result.noise_level in [NOISE_LOW, NOISE_MEDIUM]
    
    def is_suitable_for_pattern_matching(self, result: NoiseAnalysisResult) -> bool:
        """
        Check if image is suitable for pattern matching.
        
        Args:
            result: Noise analysis result
            
        Returns:
            True if noise level is LOW
        """
        return result.noise_level == NOISE_LOW