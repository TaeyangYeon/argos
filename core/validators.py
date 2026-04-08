"""
Input validation layer for the Argos vision algorithm design system.

This module provides comprehensive validation for images, ROI configurations,
and sample datasets to ensure data integrity and prevent processing errors
before they reach the core algorithms.
"""

from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from core.exceptions import InputValidationError
from core.models import ROIConfig, InspectionPurpose
from config.constants import (
    SUPPORTED_FORMATS,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    MIN_ROI_AREA_RATIO,
    NG_MINIMUM_RECOMMENDED
)


class ImageValidator:
    """Static methods for validating image files and data."""
    
    @staticmethod
    def validate_format(file_path: Union[str, Path]) -> None:
        """
        Validate that the image file format is supported.
        
        Args:
            file_path: Path to the image file
            
        Raises:
            InputValidationError: If file format is not supported
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext not in SUPPORTED_FORMATS:
            raise InputValidationError(
                f"Unsupported format: {ext}. Supported: {SUPPORTED_FORMATS}"
            )
    
    @staticmethod
    def validate_file_exists(file_path: Union[str, Path]) -> None:
        """
        Validate that the image file exists.
        
        Args:
            file_path: Path to the image file
            
        Raises:
            InputValidationError: If file does not exist
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise InputValidationError(f"File does not exist: {file_path}")
    
    @staticmethod
    def validate_resolution(image: np.ndarray) -> None:
        """
        Validate that the image resolution meets minimum requirements.
        
        Args:
            image: Loaded image array
            
        Raises:
            InputValidationError: If image is too small
        """
        height, width = image.shape[:2]
        
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            raise InputValidationError(
                f"Image too small: {width}x{height}. "
                f"Minimum: {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}"
            )
    
    @staticmethod
    def validate_not_corrupted(file_path: Union[str, Path]) -> None:
        """
        Validate that the image file is not corrupted by attempting to load it.
        
        Args:
            file_path: Path to the image file
            
        Raises:
            InputValidationError: If file appears corrupted or unreadable
        """
        file_path = Path(file_path)
        image = cv2.imread(str(file_path))
        
        if image is None:
            raise InputValidationError(
                f"File appears corrupted or unreadable: {file_path}"
            )
    
    @staticmethod
    def validate_image(file_path: Union[str, Path]) -> np.ndarray:
        """
        Run complete image validation pipeline and return loaded image.
        
        Validates in order:
        1. File exists
        2. Format is supported
        3. File is not corrupted
        4. Resolution meets requirements
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Loaded image as numpy array
            
        Raises:
            InputValidationError: If any validation step fails
        """
        file_path = Path(file_path)
        
        # Step 1: Check file exists
        ImageValidator.validate_file_exists(file_path)
        
        # Step 2: Check format is supported
        ImageValidator.validate_format(file_path)
        
        # Step 3: Check file is not corrupted (loads image)
        ImageValidator.validate_not_corrupted(file_path)
        
        # Step 4: Load image and check resolution
        image = cv2.imread(str(file_path))
        ImageValidator.validate_resolution(image)
        
        return image


class ROIValidator:
    """Static methods for validating ROI configurations."""
    
    @staticmethod
    def validate_within_bounds(roi: ROIConfig, image: np.ndarray) -> None:
        """
        Validate that ROI is within image boundaries.
        
        Args:
            roi: ROI configuration
            image: Image array for boundary checking
            
        Raises:
            InputValidationError: If ROI extends outside image boundaries
        """
        height, width = image.shape[:2]
        
        if (roi.x < 0 or roi.y < 0 or 
            roi.x + roi.width > width or 
            roi.y + roi.height > height):
            raise InputValidationError("ROI extends outside image boundaries")
    
    @staticmethod
    def validate_non_zero_size(roi: ROIConfig) -> None:
        """
        Validate that ROI has non-zero width and height.
        
        Args:
            roi: ROI configuration
            
        Raises:
            InputValidationError: If width or height is zero or negative
        """
        if roi.width <= 0 or roi.height <= 0:
            raise InputValidationError(
                "ROI width and height must be greater than zero"
            )
    
    @staticmethod
    def validate_minimum_area(roi: ROIConfig, image: np.ndarray) -> None:
        """
        Validate that ROI area meets minimum requirements.
        
        Args:
            roi: ROI configuration
            image: Image array for area comparison
            
        Raises:
            InputValidationError: If ROI area is too small
        """
        height, width = image.shape[:2]
        image_area = width * height
        roi_area = roi.width * roi.height
        ratio = roi_area / image_area
        
        if ratio < MIN_ROI_AREA_RATIO:
            raise InputValidationError(
                f"ROI area too small: {ratio:.2%} of image. "
                f"Minimum: {MIN_ROI_AREA_RATIO:.2%}"
            )
    
    @staticmethod
    def validate_roi(roi: ROIConfig, image: np.ndarray) -> None:
        """
        Run complete ROI validation pipeline.
        
        Validates in order:
        1. Non-zero size
        2. Within image bounds
        3. Minimum area requirements
        
        Args:
            roi: ROI configuration
            image: Image array for validation
            
        Raises:
            InputValidationError: If any validation step fails
        """
        # Step 1: Check non-zero size
        ROIValidator.validate_non_zero_size(roi)
        
        # Step 2: Check within bounds
        ROIValidator.validate_within_bounds(roi, image)
        
        # Step 3: Check minimum area
        ROIValidator.validate_minimum_area(roi, image)


class SampleValidator:
    """Static methods for validating sample datasets."""
    
    @staticmethod
    def validate_ng_not_empty(ng_count: int) -> None:
        """
        Validate that NG samples are not empty.
        
        Args:
            ng_count: Number of NG samples
            
        Raises:
            InputValidationError: If no NG samples provided
        """
        if ng_count == 0:
            raise InputValidationError(
                "⚠️ NG 이미지가 필요합니다. "
                "Inspection 알고리즘 설계를 위해 NG 이미지를 1장 이상 업로드해주세요."
            )
    
    @staticmethod
    def validate_ng_minimum_recommended(ng_count: int) -> Optional[str]:
        """
        Check if NG sample count meets recommended minimum.
        
        Args:
            ng_count: Number of NG samples
            
        Returns:
            Warning string if count is below recommended, None otherwise
        """
        if ng_count < NG_MINIMUM_RECOMMENDED:
            return (
                f"샘플 부족 — 정확도 신뢰도 낮음 "
                f"(현재 {ng_count}장, 권장 {NG_MINIMUM_RECOMMENDED}장 이상)"
            )
        return None
    
    @staticmethod
    def validate_ok_not_empty(ok_count: int) -> None:
        """
        Validate that OK samples are not empty.
        
        Args:
            ok_count: Number of OK samples
            
        Raises:
            InputValidationError: If no OK samples provided
        """
        if ok_count == 0:
            raise InputValidationError("OK 이미지가 최소 1장 필요합니다.")


class PurposeValidator:
    """Static methods for validating inspection purpose configurations."""
    
    @staticmethod
    def validate_not_empty(purpose: InspectionPurpose) -> None:
        """
        Validate that purpose has non-empty description and inspection_type.
        
        Args:
            purpose: InspectionPurpose instance
            
        Raises:
            InputValidationError: If description or inspection_type is empty
        """
        if purpose.description.strip() == "":
            raise InputValidationError("검사 설명이 비어있습니다.")
        
        if purpose.inspection_type.strip() == "":
            raise InputValidationError("검사 유형이 비어있습니다.")
    
    @staticmethod
    def validate_description_length(description: str) -> None:
        """
        Validate that description is at least 10 characters long.
        
        Args:
            description: Description string to validate
            
        Raises:
            InputValidationError: If description is less than 10 characters
        """
        if len(description.strip()) < 10:
            raise InputValidationError("검사 설명을 10자 이상 입력해주세요.")
    
    @staticmethod
    def validate_purpose(purpose: InspectionPurpose) -> None:
        """
        Run complete purpose validation pipeline.
        
        Validates in order:
        1. Not empty (description and inspection_type)
        2. Description length requirements
        
        Args:
            purpose: InspectionPurpose instance
            
        Raises:
            InputValidationError: If any validation step fails
        """
        # Step 1: Check not empty
        PurposeValidator.validate_not_empty(purpose)
        
        # Step 2: Check description length
        PurposeValidator.validate_description_length(purpose.description)