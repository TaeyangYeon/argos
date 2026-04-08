"""
Shape and blob feature analysis for image characterization.

This module provides comprehensive shape and blob detection capabilities including
blob contour analysis, circularity measurement, Hough circle detection, and
pattern recognition for vision algorithm design.
"""

from dataclasses import dataclass
from typing import List

import cv2
import numpy as np

from core.exceptions import RuntimeProcessingError
from core.image_processor import ImageLoader
from core.logger import get_logger


@dataclass
class BlobInfo:
    """Information about a detected blob."""
    area: float
    perimeter: float
    circularity: float      # 4π×area / perimeter²
    aspect_ratio: float     # width / height of bounding rect
    centroid_x: float
    centroid_y: float
    mean_gray: float        # mean gray level inside blob


@dataclass
class CircleInfo:
    """Information about a detected circle."""
    center_x: float
    center_y: float
    radius: float
    confidence: float       # 0.0~1.0


@dataclass
class ShapeAnalysisResult:
    """Result of shape and blob analysis."""
    blob_count: int
    blobs: List[BlobInfo]
    mean_blob_area: float
    mean_circularity: float
    has_circular_structure: bool
    detected_circles: List[CircleInfo]
    contour_complexity: float
    # mean of (perimeter² / area) for all contours
    has_repeating_pattern: bool
    pattern_description: str


class ShapeAnalyzer:
    """Analyzer for shape and blob characteristics."""
    
    def __init__(self):
        """Initialize shape analyzer."""
        self._logger = get_logger("shape_analyzer")
    
    def analyze(self, image: np.ndarray, min_area: int = 50, max_area: int = 50000) -> ShapeAnalysisResult:
        """
        Analyze shape and blob characteristics.
        
        Args:
            image: Input image (will be converted to grayscale)
            min_area: Minimum blob area to consider
            max_area: Maximum blob area to consider
            
        Returns:
            ShapeAnalysisResult with comprehensive shape analysis
        """
        # Convert to grayscale if needed
        gray = ImageLoader.to_grayscale(image)
        
        # 1. Blob detection via contours
        _, binary = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by area
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area <= area <= max_area:
                valid_contours.append(contour)
        
        # Process valid contours to create BlobInfo
        blobs = []
        total_area = 0.0
        total_circularity = 0.0
        complexity_values = []
        
        for c in valid_contours:
            area = cv2.contourArea(c)
            perimeter = cv2.arcLength(c, True)
            
            # Circularity
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter ** 2)
            else:
                circularity = 0.0
            
            # Bounding rect for aspect ratio
            x, y, w, h = cv2.boundingRect(c)
            aspect_ratio = w / h if h > 0 else 1.0
            
            # Centroid
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
            else:
                cx = 0
                cy = 0
            
            # Mean gray level inside blob
            mask = np.zeros_like(gray)
            cv2.drawContours(mask, [c], -1, 255, -1)
            mean_gray = float(cv2.mean(gray, mask)[0])
            
            blob = BlobInfo(
                area=area,
                perimeter=perimeter,
                circularity=circularity,
                aspect_ratio=aspect_ratio,
                centroid_x=cx,
                centroid_y=cy,
                mean_gray=mean_gray
            )
            blobs.append(blob)
            
            total_area += area
            total_circularity += circularity
            
            # Contour complexity
            if area > 0:
                complexity = perimeter ** 2 / area
                complexity_values.append(complexity)
        
        blob_count = len(blobs)
        mean_blob_area = total_area / blob_count if blob_count > 0 else 0.0
        mean_circularity = total_circularity / blob_count if blob_count > 0 else 0.0
        contour_complexity = np.mean(complexity_values) if complexity_values else 0.0
        
        # 2. Circular structure detection (Hough)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=0)
        
        detected_circles = []
        has_circular_structure = False
        
        if circles is not None:
            has_circular_structure = True
            circles = np.round(circles[0, :]).astype("int")
            
            for (x, y, r) in circles:
                circle_info = CircleInfo(
                    center_x=float(x),
                    center_y=float(y),
                    radius=float(r),
                    confidence=1.0  # Fixed at 1.0 since param2=30
                )
                detected_circles.append(circle_info)
        
        # 3. Repeating pattern detection
        has_repeating_pattern = False
        if blob_count >= 3:
            # Check area variance
            areas = [blob.area for blob in blobs]
            area_std = np.std(areas)
            area_mean = np.mean(areas)
            
            # Check centroid spread
            centroids_x = [blob.centroid_x for blob in blobs]
            centroids_x_std = np.std(centroids_x)
            image_width = gray.shape[1]
            
            if (area_std < area_mean * 0.3 and 
                centroids_x_std > image_width * 0.1):
                has_repeating_pattern = True
        
        # Pattern description
        if has_repeating_pattern:
            pattern_description = f"{blob_count}개의 유사한 크기 패턴 감지"
        else:
            pattern_description = "반복 패턴 없음"
        
        return ShapeAnalysisResult(
            blob_count=blob_count,
            blobs=blobs,
            mean_blob_area=mean_blob_area,
            mean_circularity=mean_circularity,
            has_circular_structure=has_circular_structure,
            detected_circles=detected_circles,
            contour_complexity=contour_complexity,
            has_repeating_pattern=has_repeating_pattern,
            pattern_description=pattern_description
        )
    
    def get_blob_overlay(self, image: np.ndarray, result: ShapeAnalysisResult) -> np.ndarray:
        """
        Returns BGR image with contours drawn in green and circle overlays in blue.
        
        Args:
            image: Input image
            result: Shape analysis result containing blob and circle information
            
        Returns:
            BGR image with overlays drawn (copy of original)
        """
        # Convert to grayscale, then back to BGR for drawing
        gray = ImageLoader.to_grayscale(image)
        overlay = ImageLoader.to_bgr(gray).copy()
        
        # Re-detect contours for drawing (using same parameters as analyze)
        _, binary = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        
        # Draw contours in green
        cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
        
        # Draw detected circles in blue
        for circle in result.detected_circles:
            center = (int(circle.center_x), int(circle.center_y))
            radius = int(circle.radius)
            cv2.circle(overlay, center, radius, (255, 0, 0), 2)
            cv2.circle(overlay, center, 2, (255, 0, 0), 3)  # Center point
        
        return overlay
    
    def suggest_inspection_method(self, result: ShapeAnalysisResult) -> List[str]:
        """
        Returns suggested inspection methods based on analysis result.
        
        Args:
            result: Shape analysis result
            
        Returns:
            List of suggested inspection method names
        """
        suggestions = []
        
        if result.has_circular_structure:
            suggestions.append("circular_caliper")
        
        if result.blob_count > 0:
            suggestions.append("blob_analysis")
        
        if result.has_repeating_pattern:
            suggestions.append("pattern_matching")
        
        if result.blob_count == 0:
            suggestions.append("edge_based")
        
        return suggestions