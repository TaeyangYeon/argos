"""
Edge strength analysis for image feature characterization.

This module provides comprehensive edge strength analysis including Sobel gradients,
edge density measurement, directional analysis, and caliper suitability assessment
for vision algorithm design.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from core.exceptions import RuntimeProcessingError
from core.image_processor import ImageLoader
from core.logger import get_logger


@dataclass
class EdgeAnalysisResult:
    """Result of edge strength analysis."""
    mean_edge_strength: float                    # average Sobel gradient magnitude
    max_edge_strength: float                     # maximum gradient magnitude
    edge_density: float                          # ratio of edge pixels to total pixels (0.0~1.0)
    dominant_direction: str                      # "horizontal" | "vertical" | "diagonal" | "mixed"
    horizontal_ratio: float                      # ratio of horizontal edge energy
    vertical_ratio: float                        # ratio of vertical edge energy
    canny_threshold_suggestion: tuple[int, int]  # (low, high) suggested Canny thresholds
    is_suitable_for_caliper: bool                # True if edges are strong and clear enough
    caliper_direction_suggestion: str            # "horizontal" | "vertical" | "both"


class EdgeAnalyzer:
    """Analyzer for edge strength and directional characteristics."""
    
    def __init__(self):
        """Initialize edge analyzer."""
        self._logger = get_logger("edge_analyzer")
    
    def analyze(self, image: np.ndarray) -> EdgeAnalysisResult:
        """
        Analyze edge strength and directional characteristics.
        
        Args:
            image: Input image (will be converted to grayscale)
            
        Returns:
            EdgeAnalysisResult with comprehensive edge analysis
        """
        # Convert to grayscale if needed
        gray = ImageLoader.to_grayscale(image)
        
        # 1. Sobel gradients
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # 2. Edge strength metrics
        mean_edge_strength = float(np.mean(magnitude))
        max_edge_strength = float(np.max(magnitude))
        
        # 3. Auto Canny thresholds (Otsu-based)
        otsu_thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        high = float(otsu_thresh) if otsu_thresh > 0 else 100.0
        low = high * 0.5
        canny_threshold_suggestion = (int(low), int(high))
        
        # Apply Canny with auto thresholds for edge density
        edges = cv2.Canny(gray, int(low), int(high))
        edge_density = float(np.count_nonzero(edges)) / edges.size
        
        # 4. Direction analysis using energy (squared magnitude)
        h_energy = float(np.sum(np.abs(sobelx)**2))
        v_energy = float(np.sum(np.abs(sobely)**2))
        total = h_energy + v_energy
        
        if total == 0:
            horizontal_ratio = 0.5
            vertical_ratio = 0.5
        else:
            horizontal_ratio = h_energy / total
            vertical_ratio = v_energy / total
        
        # Determine dominant direction
        if horizontal_ratio > 0.6:
            dominant_direction = "horizontal"
        elif vertical_ratio > 0.6:
            dominant_direction = "vertical"
        elif abs(horizontal_ratio - vertical_ratio) < 0.1:
            dominant_direction = "mixed"
        else:
            dominant_direction = "diagonal"
        
        # 5. Caliper suitability
        is_suitable_for_caliper = (mean_edge_strength >= 10.0 and edge_density >= 0.01)
        
        # 6. Caliper direction suggestion (perpendicular to dominant edge direction)
        if dominant_direction == "horizontal":
            caliper_direction_suggestion = "vertical"
        elif dominant_direction == "vertical":
            caliper_direction_suggestion = "horizontal"
        else:
            caliper_direction_suggestion = "both"
        
        return EdgeAnalysisResult(
            mean_edge_strength=mean_edge_strength,
            max_edge_strength=max_edge_strength,
            edge_density=edge_density,
            dominant_direction=dominant_direction,
            horizontal_ratio=horizontal_ratio,
            vertical_ratio=vertical_ratio,
            canny_threshold_suggestion=canny_threshold_suggestion,
            is_suitable_for_caliper=is_suitable_for_caliper,
            caliper_direction_suggestion=caliper_direction_suggestion
        )
    
    def get_edge_map(self, image: np.ndarray) -> np.ndarray:
        """
        Get Canny edge map using auto thresholds.
        
        Args:
            image: Input image
            
        Returns:
            Binary edge map (0 or 255 values)
        """
        # Convert to grayscale if needed
        gray = ImageLoader.to_grayscale(image)
        
        # Use same auto threshold logic as analyze()
        otsu_thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        high = float(otsu_thresh) if otsu_thresh > 0 else 100.0
        low = high * 0.5
        
        return cv2.Canny(gray, int(low), int(high))
    
    def compare_ok_ng(self, ok_images: list[np.ndarray], ng_images: list[np.ndarray]) -> dict:
        """
        Compare edge characteristics between OK and NG images.
        
        Args:
            ok_images: List of OK sample images
            ng_images: List of NG sample images
            
        Returns:
            Dictionary with comparison metrics
            
        Raises:
            RuntimeProcessingError: If either list is empty
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
        
        # Analyze OK images
        ok_results = [self.analyze(image) for image in ok_images]
        ok_mean_strength = np.mean([r.mean_edge_strength for r in ok_results])
        ok_edge_density = np.mean([r.edge_density for r in ok_results])
        
        # Analyze NG images
        ng_results = [self.analyze(image) for image in ng_images]
        ng_mean_strength = np.mean([r.mean_edge_strength for r in ng_results])
        ng_edge_density = np.mean([r.edge_density for r in ng_results])
        
        return {
            "ok_mean_strength": float(ok_mean_strength),
            "ng_mean_strength": float(ng_mean_strength),
            "ok_edge_density": float(ok_edge_density),
            "ng_edge_density": float(ng_edge_density),
            "strength_diff": float(ng_mean_strength - ok_mean_strength),
            "density_diff": float(ng_edge_density - ok_edge_density)
        }