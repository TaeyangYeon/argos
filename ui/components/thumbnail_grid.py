"""
Thumbnail grid component for displaying a scrollable grid of image thumbnails.

This module provides the ThumbnailGrid widget that arranges ThumbnailCard
widgets in a flowing grid layout with scrolling support.
"""

from typing import List, Optional
from PyQt6.QtWidgets import QScrollArea, QWidget
from PyQt6.QtCore import Qt, pyqtSignal

from core.image_store import ImageMeta, ImageType
from ui.components.flow_layout import FlowLayout
from ui.components.thumbnail_card import ThumbnailCard


class ThumbnailGrid(QScrollArea):
    """
    Scrollable grid of thumbnail cards.
    
    Features:
    - Scrollable viewport with flow layout
    - Dynamic card addition/removal
    - Signal forwarding from individual cards
    - Optional filtering by image type
    """
    
    # Signals forwarded from ThumbnailCard widgets
    view_requested = pyqtSignal(str)    # image_id
    delete_requested = pyqtSignal(str)  # image_id
    
    def __init__(self, image_type: Optional[ImageType] = None, parent=None):
        """
        Initialize the thumbnail grid.
        
        Args:
            image_type: Optional filter for specific image type
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._image_type_filter = image_type
        self._thumbnail_cards = []
        
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Setup the thumbnail grid UI."""
        # Configure scroll area
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create viewport widget with flow layout
        self._viewport_widget = QWidget()
        self._viewport_widget.setStyleSheet("background-color: #1A1A2E;")
        
        # Setup flow layout with proper spacing
        self._flow_layout = FlowLayout(self._viewport_widget, h_spacing=12, v_spacing=12)
        self._flow_layout.setContentsMargins(16, 16, 16, 16)
        
        # Set viewport
        self.setWidget(self._viewport_widget)
        
    def refresh(self, images: List[ImageMeta]) -> None:
        """
        Refresh the grid with new image data.
        
        Args:
            images: List of ImageMeta objects to display
        """
        # Clear existing cards
        self.clear_all()
        
        # Filter images if type filter is set
        filtered_images = images
        if self._image_type_filter is not None:
            filtered_images = [
                img for img in images 
                if img.image_type == self._image_type_filter
            ]
        
        # Create new thumbnail cards
        for image_meta in filtered_images:
            card = ThumbnailCard(image_meta)
            
            # Connect card signals to grid signals
            card.view_requested.connect(self.view_requested.emit)
            card.delete_requested.connect(self.delete_requested.emit)
            
            # Add to layout and track
            self._flow_layout.addWidget(card)
            self._thumbnail_cards.append(card)
            
        # Update layout
        self._viewport_widget.updateGeometry()
        
    def clear_all(self) -> None:
        """Remove all thumbnail cards from the grid."""
        # Remove all cards from layout and delete them
        while self._flow_layout.count() > 0:
            item = self._flow_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.deleteLater()
                
        # Clear tracking list
        self._thumbnail_cards.clear()
        
        # Update layout
        self._viewport_widget.updateGeometry()
        
    def set_image_type_filter(self, image_type: Optional[ImageType]) -> None:
        """
        Set the image type filter for the grid.
        
        Args:
            image_type: Image type to filter by, or None for no filter
        """
        self._image_type_filter = image_type
        
    def get_card_count(self) -> int:
        """
        Get the number of thumbnail cards currently in the grid.
        
        Returns:
            Number of cards
        """
        return len(self._thumbnail_cards)
        
    def get_cards(self) -> List[ThumbnailCard]:
        """
        Get all thumbnail cards in the grid.
        
        Returns:
            List of ThumbnailCard widgets
        """
        return self._thumbnail_cards.copy()