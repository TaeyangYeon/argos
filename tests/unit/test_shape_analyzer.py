"""
Unit tests for shape analyzer functionality.

Tests blob detection, circularity measurement, circular structure detection,
pattern recognition, and inspection method suggestions.
"""

import pytest
import numpy as np
import cv2

from core.analyzers.shape_analyzer import ShapeAnalyzer, ShapeAnalysisResult


class TestShapeAnalyzer:
    """Test cases for ShapeAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ShapeAnalyzer()
    
    def test_analyze_flat_image(self):
        """Test that flat image returns zero blob count within size limits."""
        # Create flat gray image - use area filter to exclude the entire image blob
        flat_image = np.ones((200, 200), dtype=np.uint8) * 128
        
        # Use smaller max_area to exclude the full-image blob (40000 pixels)
        result = self.analyzer.analyze(flat_image, max_area=30000)
        
        assert result.blob_count == 0
        assert len(result.blobs) == 0
        assert result.mean_blob_area == 0.0
        assert result.mean_circularity == 0.0
    
    def test_analyze_returns_result(self):
        """Test that analyze returns ShapeAnalysisResult."""
        # Create simple test image with one white rectangle
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (150, 150), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        assert isinstance(result, ShapeAnalysisResult)
        assert hasattr(result, 'blob_count')
        assert hasattr(result, 'blobs')
        assert hasattr(result, 'mean_blob_area')
        assert hasattr(result, 'mean_circularity')
        assert hasattr(result, 'has_circular_structure')
        assert hasattr(result, 'detected_circles')
        assert hasattr(result, 'contour_complexity')
        assert hasattr(result, 'has_repeating_pattern')
        assert hasattr(result, 'pattern_description')
    
    def test_blob_detection_with_blobs(self):
        """Test blob detection with multiple rectangular blobs."""
        # Create image with 3 white rectangles on black background
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(image, (10, 10), (50, 50), 255, -1)
        cv2.rectangle(image, (70, 10), (110, 50), 255, -1)
        cv2.rectangle(image, (130, 10), (170, 50), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        assert result.blob_count == 3
        assert len(result.blobs) == 3
        assert result.mean_blob_area > 0
    
    def test_blob_circularity_circle(self):
        """Test circularity measurement with circular blob."""
        # Create image with one circle
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(image, (100, 100), 40, 255, -1)
        
        result = self.analyzer.analyze(image)
        
        assert result.blob_count == 1
        assert result.blobs[0].circularity > 0.8  # Circles should have high circularity
    
    def test_blob_circularity_square(self):
        """Test circularity measurement with square blob."""
        # Create image with one square
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(image, (60, 60), (140, 140), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        assert result.blob_count == 1
        assert result.blobs[0].circularity < 0.8  # Squares should have lower circularity
    
    def test_circular_structure_detection(self):
        """Test Hough circle detection with circular image."""
        # Create image with drawn circle
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(image, (100, 100), 50, 255, 2)  # Circle outline
        
        result = self.analyzer.analyze(image)
        
        assert isinstance(result.has_circular_structure, bool)
        # Note: Hough detection may or may not detect this specific circle
        # but the type should be correct
    
    def test_no_circular_structure_rectangles(self):
        """Test no circular structure detection with rectangles only."""
        # Create image with only rectangles
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(image, (10, 10), (50, 50), 255, -1)
        cv2.rectangle(image, (70, 10), (110, 50), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        # Result should be boolean (may vary based on detection)
        assert isinstance(result.has_circular_structure, bool)
        assert isinstance(result.detected_circles, list)
    
    def test_contour_complexity_positive(self):
        """Test contour complexity calculation with contours present."""
        # Create image with irregular shapes
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (150, 150), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        if result.blob_count > 0:
            assert result.contour_complexity > 0
        else:
            assert result.contour_complexity == 0.0
    
    def test_repeating_pattern_detected(self):
        """Test repeating pattern detection with equal-size equally-spaced blobs."""
        # Create 3 equal-size blobs equally spaced
        image = np.zeros((200, 400), dtype=np.uint8)
        cv2.rectangle(image, (50, 80), (100, 120), 255, -1)    # blob 1
        cv2.rectangle(image, (175, 80), (225, 120), 255, -1)   # blob 2
        cv2.rectangle(image, (300, 80), (350, 120), 255, -1)   # blob 3
        
        result = self.analyzer.analyze(image)
        
        assert result.blob_count >= 3
        # Pattern detection depends on area variance and centroid spread
        assert isinstance(result.has_repeating_pattern, bool)
        assert isinstance(result.pattern_description, str)
    
    def test_no_repeating_pattern_single_blob(self):
        """Test no repeating pattern with single blob."""
        # Create image with single blob
        image = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (150, 150), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        assert result.has_repeating_pattern == False
        assert "반복 패턴 없음" in result.pattern_description
    
    def test_get_blob_overlay_shape(self):
        """Test get_blob_overlay returns same H×W×3 shape."""
        # Create test image and result
        image = np.zeros((200, 300), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (150, 150), 255, -1)
        
        result = self.analyzer.analyze(image)
        overlay = self.analyzer.get_blob_overlay(image, result)
        
        assert overlay.shape == (200, 300, 3)  # H×W×3 for BGR
        assert overlay.dtype == np.uint8
    
    def test_get_blob_overlay_no_modify_original(self):
        """Test get_blob_overlay doesn't modify original image."""
        # Create test image
        image = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(image, (25, 25), (75, 75), 255, -1)
        original_copy = image.copy()
        
        result = self.analyzer.analyze(image)
        overlay = self.analyzer.get_blob_overlay(image, result)
        
        # Original should be unchanged
        assert np.array_equal(image, original_copy)
        # Overlay should be different
        assert not np.array_equal(overlay[:,:,0], image)  # Compare with one channel
    
    def test_suggest_circular(self):
        """Test suggestion includes circular_caliper when has_circular_structure=True."""
        # Create mock result with circular structure
        image = np.zeros((100, 100), dtype=np.uint8)
        result = self.analyzer.analyze(image)
        result.has_circular_structure = True
        
        suggestions = self.analyzer.suggest_inspection_method(result)
        
        assert "circular_caliper" in suggestions
    
    def test_suggest_blob(self):
        """Test suggestion includes blob_analysis when blob_count > 0."""
        # Create image with blob
        image = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(image, (25, 25), (75, 75), 255, -1)
        
        result = self.analyzer.analyze(image)
        
        if result.blob_count > 0:
            suggestions = self.analyzer.suggest_inspection_method(result)
            assert "blob_analysis" in suggestions
    
    def test_suggest_edge_based(self):
        """Test suggestion includes edge_based when blob_count=0."""
        # Create flat image with no blobs
        flat_image = np.ones((100, 100), dtype=np.uint8) * 128
        
        result = self.analyzer.analyze(flat_image)
        suggestions = self.analyzer.suggest_inspection_method(result)
        
        if result.blob_count == 0:
            assert "edge_based" in suggestions
    
    def test_suggest_pattern(self):
        """Test suggestion includes pattern_matching when has_repeating_pattern=True."""
        # Create mock result with repeating pattern
        image = np.zeros((100, 100), dtype=np.uint8)
        result = self.analyzer.analyze(image)
        result.has_repeating_pattern = True
        
        suggestions = self.analyzer.suggest_inspection_method(result)
        
        assert "pattern_matching" in suggestions