"""
Tests for pre-flight validation logic in AnalysisPage.

This module tests the vision-type-aware image validation that ensures
the correct images are present based on the InspectionPurpose configuration.
"""

import pytest
from unittest.mock import MagicMock

from core.image_store import ImageStore, ImageType
from core.models import InspectionPurpose, ROIConfig
from ui.pages.analysis_page import AnalysisPage


class TestPreflightValidation:
    """Test pre-flight validation logic in AnalysisPage."""

    @pytest.fixture
    def mock_image_store(self):
        """Create a mock ImageStore for testing."""
        store = MagicMock(spec=ImageStore)
        
        # Default behavior: return empty lists
        store.get_all.return_value = []
        
        # Mock specific image type methods
        def mock_get_all_by_type(image_type=None):
            if image_type == ImageType.ALIGN_OK:
                return getattr(store, '_align_images', [])
            elif image_type == ImageType.INSPECTION_OK:
                return getattr(store, '_ok_images', [])
            elif image_type == ImageType.INSPECTION_NG:
                return getattr(store, '_ng_images', [])
            else:
                # Return all images if no type specified
                all_imgs = []
                all_imgs.extend(getattr(store, '_align_images', []))
                all_imgs.extend(getattr(store, '_ok_images', []))
                all_imgs.extend(getattr(store, '_ng_images', []))
                return all_imgs
        
        store.get_all = mock_get_all_by_type
        return store

    @pytest.fixture 
    def analysis_page(self, qtbot, mock_image_store):
        """Create an AnalysisPage instance for testing."""
        page = AnalysisPage(mock_image_store)
        qtbot.addWidget(page)
        return page

    def test_align_only_mode_pass_with_align_images(self, analysis_page, mock_image_store):
        """Test ALIGN-only mode passes validation when ALIGN_OK images present."""
        # Setup: ALIGN mode with ALIGN images
        purpose = InspectionPurpose(inspection_type="위치정렬")
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        
        # Mock image store to return 1 ALIGN image
        mock_image_store._align_images = [MagicMock()]  # 1 align image
        mock_image_store._ok_images = []
        mock_image_store._ng_images = []
        
        # Set purpose and ROI
        analysis_page.set_inspection_purpose(purpose)
        analysis_page.set_roi_config(roi)
        
        # Verify validation result
        result = analysis_page._validate_images_for_vision_type(1, 0, 0)
        
        assert result["align_valid"] is True
        assert result["ok_valid"] is True  # Not required for align-only
        assert result["ng_valid"] is True  # Not required for align-only
        assert result["overall_valid"] is True
        
        # Verify start button is enabled
        assert analysis_page.start_button.isEnabled() is True

    def test_align_only_mode_fail_without_align_images(self, analysis_page, mock_image_store):
        """Test ALIGN-only mode fails validation when ALIGN_OK images absent."""
        # Setup: ALIGN mode without ALIGN images
        purpose = InspectionPurpose(inspection_type="위치정렬")
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        
        # Mock image store with no images
        mock_image_store._align_images = []
        mock_image_store._ok_images = []
        mock_image_store._ng_images = []
        
        # Set purpose and ROI  
        analysis_page.set_inspection_purpose(purpose)
        analysis_page.set_roi_config(roi)
        
        # Verify validation result
        result = analysis_page._validate_images_for_vision_type(0, 0, 0)
        
        assert result["align_valid"] is False
        assert result["ok_valid"] is True  # Not required for align-only
        assert result["ng_valid"] is True  # Not required for align-only
        assert result["overall_valid"] is False
        
        # Verify start button is disabled
        assert analysis_page.start_button.isEnabled() is False

    def test_inspection_only_mode_pass_with_ok_ng_images(self, analysis_page, mock_image_store):
        """Test INSPECTION-only mode passes validation when both OK and NG images present."""
        # Setup: INSPECTION mode with OK and NG images
        purpose = InspectionPurpose(inspection_type="치수측정")
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        
        # Mock image store to return OK and NG images
        mock_image_store._align_images = []
        mock_image_store._ok_images = [MagicMock()]  # 1 OK image
        mock_image_store._ng_images = [MagicMock()]  # 1 NG image
        
        # Set purpose and ROI
        analysis_page.set_inspection_purpose(purpose)
        analysis_page.set_roi_config(roi)
        
        # Verify validation result
        result = analysis_page._validate_images_for_vision_type(0, 1, 1)
        
        assert result["align_valid"] is True  # Not required for inspection-only
        assert result["ok_valid"] is True
        assert result["ng_valid"] is True
        assert result["overall_valid"] is True
        
        # Verify start button is enabled
        assert analysis_page.start_button.isEnabled() is True

    def test_inspection_only_mode_fail_with_only_ok_images(self, analysis_page, mock_image_store):
        """Test INSPECTION-only mode fails validation when only OK images present."""
        # Setup: INSPECTION mode with only OK images
        purpose = InspectionPurpose(inspection_type="결함검출")
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        
        # Mock image store to return only OK images
        mock_image_store._align_images = []
        mock_image_store._ok_images = [MagicMock()]  # 1 OK image
        mock_image_store._ng_images = []  # No NG images
        
        # Set purpose and ROI
        analysis_page.set_inspection_purpose(purpose)
        analysis_page.set_roi_config(roi)
        
        # Verify validation result
        result = analysis_page._validate_images_for_vision_type(0, 1, 0)
        
        assert result["align_valid"] is True  # Not required for inspection-only
        assert result["ok_valid"] is True
        assert result["ng_valid"] is False  # Required but missing
        assert result["overall_valid"] is False
        
        # Verify start button is disabled
        assert analysis_page.start_button.isEnabled() is False

    def test_inspection_only_mode_fail_with_only_ng_images(self, analysis_page, mock_image_store):
        """Test INSPECTION-only mode fails validation when only NG images present."""
        # Setup: INSPECTION mode with only NG images
        purpose = InspectionPurpose(inspection_type="형상검사")
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        
        # Mock image store to return only NG images
        mock_image_store._align_images = []
        mock_image_store._ok_images = []  # No OK images
        mock_image_store._ng_images = [MagicMock()]  # 1 NG image
        
        # Set purpose and ROI
        analysis_page.set_inspection_purpose(purpose)
        analysis_page.set_roi_config(roi)
        
        # Verify validation result
        result = analysis_page._validate_images_for_vision_type(0, 0, 1)
        
        assert result["align_valid"] is True  # Not required for inspection-only
        assert result["ok_valid"] is False  # Required but missing
        assert result["ng_valid"] is True
        assert result["overall_valid"] is False
        
        # Verify start button is disabled
        assert analysis_page.start_button.isEnabled() is False

    def test_mixed_mode_pass_with_all_images(self, analysis_page, mock_image_store):
        """Test ALIGN+INSPECTION mode passes validation when all three image types present."""
        # Note: Currently, the UI doesn't support mixed mode, but we test it for future extensibility
        purpose = InspectionPurpose(inspection_type="기타")  # Will default to inspection-only
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        
        # Mock image store to return all image types
        mock_image_store._align_images = [MagicMock()]  # 1 align image
        mock_image_store._ok_images = [MagicMock()]     # 1 OK image
        mock_image_store._ng_images = [MagicMock()]     # 1 NG image
        
        # Set purpose and ROI
        analysis_page.set_inspection_purpose(purpose)
        analysis_page.set_roi_config(roi)
        
        # Verify validation result - "기타" is treated as inspection-only
        result = analysis_page._validate_images_for_vision_type(1, 1, 1)
        
        assert result["align_valid"] is True  # Not required for inspection-only
        assert result["ok_valid"] is True
        assert result["ng_valid"] is True
        assert result["overall_valid"] is True
        
        # Verify start button is enabled
        assert analysis_page.start_button.isEnabled() is True

    def test_error_message_for_align_mode(self, analysis_page):
        """Test error message for ALIGN-only mode."""
        purpose = InspectionPurpose(inspection_type="위치정렬")
        analysis_page.set_inspection_purpose(purpose)
        
        error_msg = analysis_page._get_image_validation_error_message()
        
        assert "Align 분석: ALIGN_OK 이미지가 필요합니다." == error_msg

    def test_error_message_for_inspection_mode(self, analysis_page):
        """Test error message for INSPECTION-only mode."""
        purpose = InspectionPurpose(inspection_type="치수측정")
        analysis_page.set_inspection_purpose(purpose)
        
        error_msg = analysis_page._get_image_validation_error_message()
        
        assert "Inspection 분석: OK 및 NG 이미지가 모두 필요합니다." == error_msg

    def test_error_message_without_purpose(self, analysis_page):
        """Test error message when no inspection purpose is set."""
        error_msg = analysis_page._get_image_validation_error_message()
        
        assert "검사 목적이 설정되지 않았습니다." == error_msg

    def test_validation_all_inspection_types(self, analysis_page):
        """Test that all known inspection types are handled correctly."""
        inspection_types = ["치수측정", "결함검출", "형상검사", "위치정렬", "기타"]
        
        for inspection_type in inspection_types:
            purpose = InspectionPurpose(inspection_type=inspection_type)
            analysis_page.set_inspection_purpose(purpose)
            
            if inspection_type == "위치정렬":
                # ALIGN-only mode
                result = analysis_page._validate_images_for_vision_type(1, 0, 0)
                assert result["overall_valid"] is True
                
                result = analysis_page._validate_images_for_vision_type(0, 0, 0)
                assert result["overall_valid"] is False
            else:
                # INSPECTION-only mode
                result = analysis_page._validate_images_for_vision_type(0, 1, 1)
                assert result["overall_valid"] is True
                
                result = analysis_page._validate_images_for_vision_type(0, 1, 0)
                assert result["overall_valid"] is False
                
                result = analysis_page._validate_images_for_vision_type(0, 0, 1)
                assert result["overall_valid"] is False

    def test_validation_without_roi_or_purpose(self, analysis_page, mock_image_store):
        """Test validation behavior when ROI or purpose is missing."""
        # Mock image store with all image types
        mock_image_store._align_images = [MagicMock()]
        mock_image_store._ok_images = [MagicMock()]
        mock_image_store._ng_images = [MagicMock()]
        
        # Test without purpose (ROI is set)
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        analysis_page.set_roi_config(roi)
        
        assert analysis_page.start_button.isEnabled() is False
        
        # Test without ROI (purpose is set)
        analysis_page.roi_config = None  # Clear ROI
        purpose = InspectionPurpose(inspection_type="위치정렬")
        analysis_page.set_inspection_purpose(purpose)
        
        assert analysis_page.start_button.isEnabled() is False
        
        # Test with both ROI and purpose
        analysis_page.set_roi_config(roi)
        
        assert analysis_page.start_button.isEnabled() is True

    def test_unknown_inspection_type_fallback(self, analysis_page):
        """Test that unknown inspection types fall back to requiring all images."""
        purpose = InspectionPurpose(inspection_type="알 수 없는 타입")
        analysis_page.set_inspection_purpose(purpose)
        
        # Should require all image types
        result = analysis_page._validate_images_for_vision_type(1, 1, 1)
        assert result["overall_valid"] is True
        
        result = analysis_page._validate_images_for_vision_type(1, 0, 1)
        assert result["overall_valid"] is False
        
        result = analysis_page._validate_images_for_vision_type(0, 1, 1)
        assert result["overall_valid"] is False