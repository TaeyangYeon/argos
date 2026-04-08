"""
Histogram and brightness analysis for image features.

This module provides histogram analysis capabilities for quantitative 
image assessment including brightness statistics, distribution analysis,
and OK/NG separation scoring.
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from core.exceptions import RuntimeProcessingError
from core.image_processor import ImageLoader
from core.logger import get_logger


@dataclass
class HistogramAnalysisResult:
    """Result of histogram analysis."""
    mean_gray: float          # average gray level 0~255
    std_gray: float           # standard deviation
    min_gray: int             # minimum gray value
    max_gray: int             # maximum gray value
    dynamic_range: int        # max_gray - min_gray
    peak_count: int           # number of histogram peaks
    distribution_type: str    # "bimodal"|"unimodal"|"flat"
    ok_mean: Optional[float] = None
    ng_mean: Optional[float] = None
    separation_score: Optional[float] = None


class HistogramAnalyzer:
    """Analyzer for histogram and brightness features."""
    
    def __init__(self):
        """Initialize histogram analyzer."""
        self._logger = get_logger("histogram_analyzer")
    
    def analyze_single(self, image: np.ndarray) -> HistogramAnalysisResult:
        """
        Analyze single image histogram features.
        
        Args:
            image: Input image (will be converted to grayscale)
            
        Returns:
            HistogramAnalysisResult with calculated features
        """
        # Convert to grayscale if needed
        gray = ImageLoader.to_grayscale(image)
        
        # Calculate basic statistics
        mean_gray = float(np.mean(gray))
        std_gray = float(np.std(gray))
        min_gray = int(np.min(gray))
        max_gray = int(np.max(gray))
        dynamic_range = max_gray - min_gray
        
        # Calculate histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        
        # Count peaks
        peak_count = self._count_peaks(hist)
        
        # Determine distribution type
        if peak_count >= 2:
            distribution_type = "bimodal"
        elif peak_count == 1:
            distribution_type = "unimodal"
        else:
            distribution_type = "flat"
        
        return HistogramAnalysisResult(
            mean_gray=mean_gray,
            std_gray=std_gray,
            min_gray=min_gray,
            max_gray=max_gray,
            dynamic_range=dynamic_range,
            peak_count=peak_count,
            distribution_type=distribution_type
        )
    
    def analyze_separation(self, 
                         ok_images: list[np.ndarray], 
                         ng_images: list[np.ndarray]) -> HistogramAnalysisResult:
        """
        Analyze histogram separation between OK and NG images.
        
        Args:
            ok_images: List of OK images
            ng_images: List of NG images
            
        Returns:
            HistogramAnalysisResult with separation analysis
            
        Raises:
            RuntimeProcessingError: If either image list is empty
        """
        if not ok_images:
            RuntimeProcessingError.raise_with_log(
                "OK images list is empty", 
                self._logger
            )
        
        if not ng_images:
            RuntimeProcessingError.raise_with_log(
                "NG images list is empty", 
                self._logger
            )
        
        # Calculate mean gray for OK images
        ok_means = []
        for image in ok_images:
            gray = ImageLoader.to_grayscale(image)
            ok_means.append(float(np.mean(gray)))
        ok_mean = np.mean(ok_means)
        
        # Calculate mean gray for NG images
        ng_means = []
        for image in ng_images:
            gray = ImageLoader.to_grayscale(image)
            ng_means.append(float(np.mean(gray)))
        ng_mean = np.mean(ng_means)
        
        # Calculate separation score
        separation_score = round(abs(ok_mean - ng_mean) / 255 * 100, 2)
        
        # Use first OK image for basic stats
        result = self.analyze_single(ok_images[0])
        
        # Add separation data
        result.ok_mean = ok_mean
        result.ng_mean = ng_mean
        result.separation_score = separation_score
        
        return result
    
    def get_histogram_data(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Get histogram data for plotting.
        
        Args:
            image: Input image
            
        Returns:
            Tuple of (bin_edges, hist_values)
            bin_edges: shape (256,) with bin centers 0-255
            hist_values: shape (256,) normalized 0-1
        """
        gray = ImageLoader.to_grayscale(image)
        
        # Calculate histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        
        # Normalize histogram
        if hist.max() > 0:
            hist_values = hist / hist.max()
        else:
            hist_values = np.zeros_like(hist)
        
        # Bin edges (centers 0-255)
        bin_edges = np.arange(256)
        
        return bin_edges, hist_values
    
    def is_sufficient_contrast(self, 
                             result: HistogramAnalysisResult, 
                             min_dynamic_range: int = 50) -> bool:
        """
        Check if image has sufficient contrast.
        
        Args:
            result: Histogram analysis result
            min_dynamic_range: Minimum required dynamic range
            
        Returns:
            True if dynamic range is sufficient
        """
        return result.dynamic_range >= min_dynamic_range
    
    def suggest_preprocessing(self, result: HistogramAnalysisResult) -> list[str]:
        """
        Suggest preprocessing steps based on histogram analysis.
        
        Args:
            result: Histogram analysis result
            
        Returns:
            List of suggested preprocessing step names
        """
        suggestions = []
        
        # Low dynamic range
        if result.dynamic_range < 50:
            suggestions.append("histogram_equalization")
        
        # Low standard deviation
        if result.std_gray < 20:
            suggestions.append("clahe")
        
        # Flat distribution
        if result.distribution_type == "flat":
            suggestions.append("normalize")
        
        # Too dark
        if result.mean_gray < 50:
            suggestions.append("normalize")
        
        # Too bright
        if result.mean_gray > 200:
            suggestions.append("normalize")
        
        return suggestions
    
    def _smooth_histogram(self, hist: np.ndarray) -> np.ndarray:
        """
        Smooth histogram using Gaussian blur.
        
        Args:
            hist: Histogram array shape (256,)
            
        Returns:
            Smoothed histogram
        """
        # Reshape for cv2.GaussianBlur
        hist_reshaped = hist.reshape(256, 1)
        smoothed = cv2.GaussianBlur(hist_reshaped, (1, 5), 0)
        return smoothed.flatten()
    
    def _count_peaks(self, hist: np.ndarray) -> int:
        """
        Count peaks in histogram.
        
        Args:
            hist: Histogram array
            
        Returns:
            Number of detected peaks
        """
        # Smooth histogram
        smoothed = self._smooth_histogram(hist)
        
        # Calculate threshold
        threshold = np.mean(smoothed) * 0.5
        
        # Find peaks
        peak_count = 0
        for i in range(1, len(smoothed) - 1):
            if (smoothed[i] > smoothed[i-1] and 
                smoothed[i] > smoothed[i+1] and 
                smoothed[i] > threshold):
                peak_count += 1
        
        return peak_count