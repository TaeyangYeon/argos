"""
Image data model and repository for the Argos vision algorithm design system.

This module provides in-memory storage and management for uploaded images,
including metadata tracking, thumbnail generation, and categorization by type.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import cv2
import numpy as np

from core.exceptions import InputValidationError, RuntimeProcessingError
from core.logger import get_logger
from core.validators import ImageValidator, SampleValidator


class ImageType(Enum):
    """Categories for uploaded images."""
    ALIGN_OK = "align_ok"
    INSPECTION_OK = "inspection_ok"
    INSPECTION_NG = "inspection_ng"


@dataclass
class ImageMeta:
    """Metadata for a stored image."""
    id: str
    file_path: str
    image_type: ImageType
    width: int
    height: int
    file_size_bytes: int
    added_at: str
    thumbnail: Optional[np.ndarray] = None


class ImageStore:
    """
    In-memory repository for managing uploaded images and their metadata.
    
    Provides CRUD operations, categorization, validation, and thumbnail generation
    while maintaining clean separation between storage and business logic.
    """
    
    def __init__(self):
        """Initialize empty image store."""
        self._images: Dict[str, ImageMeta] = {}
        self._logger = get_logger("image_store")
    
    def add(self, file_path: Union[str, Path], image_type: ImageType) -> ImageMeta:
        """
        Add an image to the store after validation.
        
        Args:
            file_path: Path to the image file
            image_type: Category for the image
            
        Returns:
            ImageMeta object for the added image
            
        Raises:
            InputValidationError: If image validation fails
            RuntimeProcessingError: If file operations fail
        """
        file_path = Path(file_path)
        
        # Validate the image using the existing validator
        image = ImageValidator.validate_image(file_path)
        
        # Generate unique ID
        image_id = str(uuid.uuid4())
        
        # Get image dimensions and file size
        height, width = image.shape[:2]
        try:
            file_size_bytes = file_path.stat().st_size
        except OSError as e:
            raise RuntimeProcessingError(f"Failed to read file size: {e}")
        
        # Generate thumbnail
        thumbnail = self._generate_thumbnail(image)
        
        # Create metadata object
        meta = ImageMeta(
            id=image_id,
            file_path=str(file_path.absolute()),
            image_type=image_type,
            width=width,
            height=height,
            file_size_bytes=file_size_bytes,
            added_at=datetime.utcnow().isoformat(),
            thumbnail=thumbnail
        )
        
        # Store the metadata
        self._images[image_id] = meta
        
        # Log addition (filename only for privacy)
        self._logger.info(f"Added {image_type.value} image: {file_path.name}")
        
        return meta
    
    def remove(self, image_id: str) -> None:
        """
        Remove an image from the store.
        
        Args:
            image_id: ID of the image to remove
            
        Raises:
            InputValidationError: If image ID not found
        """
        if image_id not in self._images:
            raise InputValidationError(f"Image not found: {image_id}")
        
        meta = self._images[image_id]
        del self._images[image_id]
        
        self._logger.info(f"Removed {meta.image_type.value} image: {Path(meta.file_path).name}")
    
    def get(self, image_id: str) -> Optional[ImageMeta]:
        """
        Get image metadata by ID.
        
        Args:
            image_id: ID of the image
            
        Returns:
            ImageMeta object or None if not found
        """
        return self._images.get(image_id)
    
    def get_all(self, image_type: Optional[ImageType] = None) -> List[ImageMeta]:
        """
        Get all images, optionally filtered by type.
        
        Args:
            image_type: Optional filter by image type
            
        Returns:
            List of ImageMeta objects sorted by added_at
        """
        images = list(self._images.values())
        
        if image_type is not None:
            images = [img for img in images if img.image_type == image_type]
        
        # Sort by added_at ascending
        images.sort(key=lambda img: img.added_at)
        
        return images
    
    def count(self, image_type: Optional[ImageType] = None) -> int:
        """
        Count images, optionally filtered by type.
        
        Args:
            image_type: Optional filter by image type
            
        Returns:
            Number of images
        """
        if image_type is None:
            return len(self._images)
        
        return sum(1 for img in self._images.values() 
                  if img.image_type == image_type)
    
    def clear(self, image_type: Optional[ImageType] = None) -> None:
        """
        Clear all images or only those of specified type.
        
        Args:
            image_type: Optional filter to clear only specific type
        """
        if image_type is None:
            cleared_count = len(self._images)
            self._images.clear()
            self._logger.info(f"Cleared all {cleared_count} images")
        else:
            # Remove only images of specified type
            to_remove = [img_id for img_id, meta in self._images.items()
                        if meta.image_type == image_type]
            
            for img_id in to_remove:
                del self._images[img_id]
            
            self._logger.info(f"Cleared {len(to_remove)} {image_type.value} images")
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics for all stored images.
        
        Returns:
            Dictionary with counts and warning information
        """
        align_ok_count = self.count(ImageType.ALIGN_OK)
        inspection_ok_count = self.count(ImageType.INSPECTION_OK)
        inspection_ng_count = self.count(ImageType.INSPECTION_NG)
        total_count = len(self._images)
        
        # Check for NG sample warning using SampleValidator
        ng_warning = SampleValidator.validate_ng_minimum_recommended(inspection_ng_count)
        
        return {
            "align_ok": align_ok_count,
            "inspection_ok": inspection_ok_count,
            "inspection_ng": inspection_ng_count,
            "total": total_count,
            "ng_warning": ng_warning
        }
    
    def load_image(self, image_id: str) -> np.ndarray:
        """
        Load full-resolution image from file.
        
        Args:
            image_id: ID of the image to load
            
        Returns:
            Full-resolution image as numpy array
            
        Raises:
            InputValidationError: If image ID not found
            RuntimeProcessingError: If loading fails
        """
        meta = self.get(image_id)
        if meta is None:
            raise InputValidationError(f"Image not found: {image_id}")
        
        try:
            image = cv2.imread(meta.file_path)
            if image is None:
                raise RuntimeProcessingError(f"Failed to load image: {Path(meta.file_path).name}")
            return image
        except Exception as e:
            raise RuntimeProcessingError(f"Failed to load image: {e}")
    
    def add_image(self, image_meta: ImageMeta) -> None:
        """
        Add a pre-created ImageMeta object to the store.
        
        This is primarily used for testing when you have synthetic ImageMeta objects.
        
        Args:
            image_meta: Pre-created ImageMeta object
        """
        self._images[image_meta.id] = image_meta
        self._logger.debug(f"Added pre-created image {image_meta.id} ({image_meta.image_type.value})")
    
    def _generate_thumbnail(self, image: np.ndarray, max_size: int = 128) -> np.ndarray:
        """
        Generate a thumbnail image preserving aspect ratio.
        
        Args:
            image: Original image
            max_size: Maximum dimension for thumbnail
            
        Returns:
            Thumbnail image
        """
        height, width = image.shape[:2]
        
        # Calculate scaling factor to fit within max_size
        scale = min(max_size / width, max_size / height)
        
        if scale >= 1.0:
            # Image is already small enough
            return image.copy()
        
        # Calculate new dimensions
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize using INTER_AREA for best quality when downsampling
        thumbnail = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return thumbnail