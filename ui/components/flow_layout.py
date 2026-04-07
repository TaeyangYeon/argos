"""
Flow layout component for arranging widgets in rows with wrapping.

This module provides a custom QLayout that arranges widgets in a left-to-right
flow, wrapping to the next row when the available width is exceeded.
"""

from PyQt6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget
from PyQt6.QtCore import QRect, QSize, Qt


class FlowLayout(QLayout):
    """
    A custom QLayout that arranges widgets in a left-to-right flow.
    
    Features:
    - Widgets wrap to next row when width is exceeded
    - Configurable horizontal and vertical spacing
    - Proper size hints and minimum size calculations
    - Support for dynamic resizing
    """
    
    def __init__(self, parent=None, h_spacing: int = 12, v_spacing: int = 12):
        """
        Initialize the flow layout.
        
        Args:
            parent: Parent widget
            h_spacing: Horizontal spacing between widgets
            v_spacing: Vertical spacing between rows
        """
        super().__init__(parent)
        
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items = []
        
    def addItem(self, item: QLayoutItem) -> None:
        """Add a layout item to the flow layout."""
        self._items.append(item)
        
    def count(self) -> int:
        """Return the number of items in the layout."""
        return len(self._items)
        
    def itemAt(self, index: int) -> QLayoutItem | None:
        """Return the layout item at the given index."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
        
    def takeAt(self, index: int) -> QLayoutItem | None:
        """Remove and return the layout item at the given index."""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
        
    def hasHeightForWidth(self) -> bool:
        """Return True since this layout's height depends on width."""
        return True
        
    def heightForWidth(self, width: int) -> int:
        """
        Calculate the height needed for the given width.
        
        Args:
            width: Available width
            
        Returns:
            Required height
        """
        height = self._doLayout(QRect(0, 0, width, 0), True)
        return height
        
    def setGeometry(self, rect: QRect) -> None:
        """Set the layout geometry and arrange items."""
        super().setGeometry(rect)
        self._doLayout(rect, False)
        
    def sizeHint(self) -> QSize:
        """Return the preferred size for the layout."""
        size = QSize()
        
        for item in self._items:
            item_size = item.sizeHint()
            size = size.expandedTo(item_size)
            
        # Add margins
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                     margins.top() + margins.bottom())
                     
        return size
        
    def minimumSize(self) -> QSize:
        """Return the minimum size for the layout."""
        size = QSize()
        
        for item in self._items:
            item_size = item.minimumSize()
            size = size.expandedTo(item_size)
            
        # Add margins
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                     margins.top() + margins.bottom())
                     
        return size
        
    def _doLayout(self, rect: QRect, test_only: bool) -> int:
        """
        Arrange the layout items within the given rectangle.
        
        Args:
            rect: Available rectangle
            test_only: If True, only calculate height without positioning
            
        Returns:
            Total height used
        """
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(),
                                     -margins.right(), -margins.bottom())
        
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        
        for item in self._items:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue
                
            size_hint = item.sizeHint()
            space_x = self._h_spacing
            space_y = self._v_spacing
            
            # Check if item fits in current row
            next_x = x + size_hint.width() + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                # Move to next row
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + size_hint.width() + space_x
                line_height = 0
                
            if not test_only:
                item.setGeometry(QRect(x, y, size_hint.width(), size_hint.height()))
                
            x = next_x
            line_height = max(line_height, size_hint.height())
            
        return y + line_height - rect.y() + margins.bottom()