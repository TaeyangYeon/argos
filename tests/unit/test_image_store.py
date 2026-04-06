"""
Unit tests for the image store repository system.

Tests all functionality of the ImageStore class including CRUD operations,
validation integration, thumbnail generation, and summary statistics.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from core.exceptions import InputValidationError, RuntimeProcessingError
from core.image_store import ImageStore, ImageType, ImageMeta


class TestImageStore:
    """Tests for the ImageStore repository class."""
    
    def create_test_image(self, tmp_path, width=100, height=100, name="test.png"):
        """Helper to create a test image file."""
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[10:90, 10:90] = [100, 150, 200]  # Add some content
        
        image_path = tmp_path / name
        cv2.imwrite(str(image_path), image)
        return image_path
    
    def test_add_valid_image_align_ok(self, tmp_path):
        """Test adding a valid PNG as ALIGN_OK returns correct ImageMeta."""
        store = ImageStore()
        image_path = self.create_test_image(tmp_path, name="align_test.png")
        
        meta = store.add(image_path, ImageType.ALIGN_OK)
        
        assert isinstance(meta, ImageMeta)
        assert meta.image_type == ImageType.ALIGN_OK
        assert meta.width == 100
        assert meta.height == 100
        assert meta.file_size_bytes > 0
        assert meta.thumbnail is not None
        assert meta.id is not None
        assert meta.added_at is not None
    
    def test_add_valid_image_inspection_ng(self, tmp_path):
        """Test adding a valid PNG as INSPECTION_NG is stored correctly."""
        store = ImageStore()
        image_path = self.create_test_image(tmp_path, name="ng_test.png")
        
        meta = store.add(image_path, ImageType.INSPECTION_NG)
        
        assert meta.image_type == ImageType.INSPECTION_NG
        assert store.count(ImageType.INSPECTION_NG) == 1
        assert store.count() == 1
    
    def test_add_invalid_format_raises(self, tmp_path):
        """Test adding a .gif file raises InputValidationError."""
        store = ImageStore()
        
        # Create a file with unsupported extension
        gif_path = tmp_path / "test.gif"
        gif_path.write_text("fake gif content")
        
        with pytest.raises(InputValidationError, match="Unsupported format"):
            store.add(gif_path, ImageType.ALIGN_OK)
    
    def test_add_corrupted_file_raises(self, tmp_path):
        """Test adding a corrupted file raises InputValidationError."""
        store = ImageStore()
        
        # Create a file with PNG extension but corrupted content
        corrupted_path = tmp_path / "corrupted.png"
        corrupted_path.write_bytes(b"this is not a valid PNG file")
        
        with pytest.raises(InputValidationError, match="File appears corrupted"):
            store.add(corrupted_path, ImageType.ALIGN_OK)
    
    def test_remove_existing_image(self, tmp_path):
        """Test adding then removing an image decreases count by 1."""
        store = ImageStore()
        image_path = self.create_test_image(tmp_path)
        
        # Add an image
        meta = store.add(image_path, ImageType.ALIGN_OK)
        assert store.count() == 1
        
        # Remove the image
        store.remove(meta.id)
        assert store.count() == 0
    
    def test_remove_nonexistent_raises(self):
        """Test removing with fake id raises InputValidationError."""
        store = ImageStore()
        
        with pytest.raises(InputValidationError, match="Image not found"):
            store.remove("nonexistent-id")
    
    def test_get_returns_correct_meta(self, tmp_path):
        """Test adding image then getting by id returns same ImageMeta."""
        store = ImageStore()
        image_path = self.create_test_image(tmp_path)
        
        original_meta = store.add(image_path, ImageType.INSPECTION_OK)
        retrieved_meta = store.get(original_meta.id)
        
        assert retrieved_meta is not None
        assert retrieved_meta.id == original_meta.id
        assert retrieved_meta.image_type == original_meta.image_type
        assert retrieved_meta.width == original_meta.width
        assert retrieved_meta.height == original_meta.height
    
    def test_get_returns_none_if_not_found(self):
        """Test get with nonexistent id returns None."""
        store = ImageStore()
        
        result = store.get("nonexistent-id")
        
        assert result is None
    
    def test_get_all_no_filter(self, tmp_path):
        """Test adding 3 images of mixed types and get_all returns all 3."""
        store = ImageStore()
        
        # Add three different images
        path1 = self.create_test_image(tmp_path, name="img1.png")
        path2 = self.create_test_image(tmp_path, name="img2.png")
        path3 = self.create_test_image(tmp_path, name="img3.png")
        
        store.add(path1, ImageType.ALIGN_OK)
        store.add(path2, ImageType.INSPECTION_OK)
        store.add(path3, ImageType.INSPECTION_NG)
        
        all_images = store.get_all()
        
        assert len(all_images) == 3
        # Check that different types are present
        types = {img.image_type for img in all_images}
        assert len(types) == 3  # All three types should be present
    
    def test_get_all_filtered_by_type(self, tmp_path):
        """Test adding 2 OK + 1 NG and get_all(INSPECTION_NG) returns 1."""
        store = ImageStore()
        
        # Add multiple images
        path1 = self.create_test_image(tmp_path, name="ok1.png")
        path2 = self.create_test_image(tmp_path, name="ok2.png")
        path3 = self.create_test_image(tmp_path, name="ng1.png")
        
        store.add(path1, ImageType.INSPECTION_OK)
        store.add(path2, ImageType.INSPECTION_OK)
        store.add(path3, ImageType.INSPECTION_NG)
        
        ng_images = store.get_all(ImageType.INSPECTION_NG)
        
        assert len(ng_images) == 1
        assert ng_images[0].image_type == ImageType.INSPECTION_NG
    
    def test_get_all_sorted_by_added_at(self, tmp_path):
        """Test that get_all returns images sorted by added_at ascending."""
        store = ImageStore()
        
        # Add images in sequence
        path1 = self.create_test_image(tmp_path, name="first.png")
        path2 = self.create_test_image(tmp_path, name="second.png")
        
        meta1 = store.add(path1, ImageType.ALIGN_OK)
        meta2 = store.add(path2, ImageType.ALIGN_OK)
        
        all_images = store.get_all()
        
        assert len(all_images) == 2
        assert all_images[0].added_at <= all_images[1].added_at
        assert all_images[0].id == meta1.id  # First added should be first in list
        assert all_images[1].id == meta2.id
    
    def test_count_total(self, tmp_path):
        """Test adding 3 images and count() == 3."""
        store = ImageStore()
        
        # Add three images
        for i in range(3):
            path = self.create_test_image(tmp_path, name=f"img{i}.png")
            store.add(path, ImageType.ALIGN_OK)
        
        assert store.count() == 3
    
    def test_count_filtered(self, tmp_path):
        """Test adding 2 ALIGN_OK + 1 NG and count(ALIGN_OK) == 2."""
        store = ImageStore()
        
        # Add different types
        path1 = self.create_test_image(tmp_path, name="align1.png")
        path2 = self.create_test_image(tmp_path, name="align2.png")
        path3 = self.create_test_image(tmp_path, name="ng1.png")
        
        store.add(path1, ImageType.ALIGN_OK)
        store.add(path2, ImageType.ALIGN_OK)
        store.add(path3, ImageType.INSPECTION_NG)
        
        assert store.count(ImageType.ALIGN_OK) == 2
        assert store.count(ImageType.INSPECTION_NG) == 1
        assert store.count() == 3
    
    def test_clear_all(self, tmp_path):
        """Test adding 3 images, clear(), and count() == 0."""
        store = ImageStore()
        
        # Add multiple images
        for i in range(3):
            path = self.create_test_image(tmp_path, name=f"img{i}.png")
            store.add(path, ImageType.ALIGN_OK)
        
        assert store.count() == 3
        
        store.clear()
        
        assert store.count() == 0
    
    def test_clear_by_type(self, tmp_path):
        """Test adding 2 OK + 1 NG, clear(INSPECTION_NG), and count() == 2."""
        store = ImageStore()
        
        # Add different types
        path1 = self.create_test_image(tmp_path, name="ok1.png")
        path2 = self.create_test_image(tmp_path, name="ok2.png")
        path3 = self.create_test_image(tmp_path, name="ng1.png")
        
        store.add(path1, ImageType.INSPECTION_OK)
        store.add(path2, ImageType.INSPECTION_OK)
        store.add(path3, ImageType.INSPECTION_NG)
        
        assert store.count() == 3
        
        store.clear(ImageType.INSPECTION_NG)
        
        assert store.count() == 2
        assert store.count(ImageType.INSPECTION_NG) == 0
        assert store.count(ImageType.INSPECTION_OK) == 2
    
    def test_get_summary_structure(self, tmp_path):
        """Test adding 1 ALIGN_OK, 2 INSPECTION_OK, 1 INSPECTION_NG and summary is correct."""
        store = ImageStore()
        
        # Add specific counts of each type
        align_path = self.create_test_image(tmp_path, name="align.png")
        ok1_path = self.create_test_image(tmp_path, name="ok1.png")
        ok2_path = self.create_test_image(tmp_path, name="ok2.png")
        ng_path = self.create_test_image(tmp_path, name="ng.png")
        
        store.add(align_path, ImageType.ALIGN_OK)
        store.add(ok1_path, ImageType.INSPECTION_OK)
        store.add(ok2_path, ImageType.INSPECTION_OK)
        store.add(ng_path, ImageType.INSPECTION_NG)
        
        summary = store.get_summary()
        
        assert summary["align_ok"] == 1
        assert summary["inspection_ok"] == 2
        assert summary["inspection_ng"] == 1
        assert summary["total"] == 4
        assert "ng_warning" in summary
    
    def test_get_summary_ng_warning(self, tmp_path):
        """Test adding 0 NG and summary ng_warning is not None."""
        store = ImageStore()
        
        # Add only non-NG images
        align_path = self.create_test_image(tmp_path, name="align.png")
        store.add(align_path, ImageType.ALIGN_OK)
        
        summary = store.get_summary()
        
        assert summary["inspection_ng"] == 0
        assert summary["ng_warning"] is not None
        assert "샘플 부족" in summary["ng_warning"]
    
    def test_get_summary_ng_sufficient(self, tmp_path):
        """Test adding 3 NG and summary ng_warning is None."""
        store = ImageStore()
        
        # Add sufficient NG images
        for i in range(3):
            path = self.create_test_image(tmp_path, name=f"ng{i}.png")
            store.add(path, ImageType.INSPECTION_NG)
        
        summary = store.get_summary()
        
        assert summary["inspection_ng"] == 3
        assert summary["ng_warning"] is None
    
    def test_load_image_returns_ndarray(self, tmp_path):
        """Test adding image and load_image(id) returns np.ndarray."""
        store = ImageStore()
        image_path = self.create_test_image(tmp_path, width=200, height=150)
        
        meta = store.add(image_path, ImageType.ALIGN_OK)
        loaded_image = store.load_image(meta.id)
        
        assert isinstance(loaded_image, np.ndarray)
        assert loaded_image.shape[:2] == (150, 200)  # height, width
    
    def test_load_image_nonexistent_raises(self):
        """Test load_image with nonexistent id raises InputValidationError."""
        store = ImageStore()
        
        with pytest.raises(InputValidationError, match="Image not found"):
            store.load_image("nonexistent-id")
    
    def test_thumbnail_generated(self, tmp_path):
        """Test adding image generates thumbnail that is not None."""
        store = ImageStore()
        image_path = self.create_test_image(tmp_path)
        
        meta = store.add(image_path, ImageType.ALIGN_OK)
        
        assert meta.thumbnail is not None
        assert isinstance(meta.thumbnail, np.ndarray)
    
    def test_thumbnail_max_size(self, tmp_path):
        """Test adding 512x512 image creates thumbnail with max dimension <= 128."""
        store = ImageStore()
        
        # Create a large image
        large_image = np.zeros((512, 512, 3), dtype=np.uint8)
        large_image[100:400, 100:400] = [100, 150, 200]
        
        large_path = tmp_path / "large.png"
        cv2.imwrite(str(large_path), large_image)
        
        meta = store.add(large_path, ImageType.ALIGN_OK)
        
        assert meta.thumbnail is not None
        thumb_height, thumb_width = meta.thumbnail.shape[:2]
        assert max(thumb_width, thumb_height) <= 128
        assert min(thumb_width, thumb_height) > 0  # Should not be empty
    
    def test_thumbnail_preserves_aspect_ratio(self, tmp_path):
        """Test thumbnail preserves aspect ratio of original image."""
        store = ImageStore()
        
        # Create a rectangular image (2:1 aspect ratio)
        rect_image = np.zeros((200, 400, 3), dtype=np.uint8)
        rect_image[50:150, 100:300] = [100, 150, 200]
        
        rect_path = tmp_path / "rectangle.png"
        cv2.imwrite(str(rect_path), rect_image)
        
        meta = store.add(rect_path, ImageType.ALIGN_OK)
        
        thumb_height, thumb_width = meta.thumbnail.shape[:2]
        original_ratio = 400 / 200  # width/height = 2.0
        thumb_ratio = thumb_width / thumb_height
        
        # Allow small floating point differences
        assert abs(thumb_ratio - original_ratio) < 0.01
    
    def test_small_image_thumbnail(self, tmp_path):
        """Test that small images still get thumbnails."""
        store = ImageStore()
        
        # Create a small image (64x64)
        small_image = np.zeros((64, 64, 3), dtype=np.uint8)
        small_image[10:50, 10:50] = [100, 150, 200]
        
        small_path = tmp_path / "small.png"
        cv2.imwrite(str(small_path), small_image)
        
        meta = store.add(small_path, ImageType.ALIGN_OK)
        
        # Even small images should have thumbnails
        assert meta.thumbnail is not None
        # For images already smaller than max_size, thumbnail should be a copy
        thumb_height, thumb_width = meta.thumbnail.shape[:2]
        assert thumb_width == 64
        assert thumb_height == 64
    
    def test_store_independence(self, tmp_path):
        """Test that different ImageStore instances are independent."""
        store1 = ImageStore()
        store2 = ImageStore()
        
        image_path = self.create_test_image(tmp_path)
        
        # Add to first store only
        store1.add(image_path, ImageType.ALIGN_OK)
        
        assert store1.count() == 1
        assert store2.count() == 0  # Second store should be empty
    
    def test_file_path_absolute(self, tmp_path):
        """Test that file_path is stored as absolute path."""
        store = ImageStore()
        
        # Use relative path
        relative_path = Path("tests/fixtures/sample_ok.png")
        
        meta = store.add(relative_path, ImageType.ALIGN_OK)
        
        # Should be converted to absolute path
        assert Path(meta.file_path).is_absolute()
        assert meta.file_path.endswith("sample_ok.png")