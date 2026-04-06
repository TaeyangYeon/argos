"""
Tests for the sidebar navigation component.

This module tests the ArgosSidebar and SidebarMenuItem classes,
including navigation, collapse/expand functionality, and progress tracking.
"""

import pytest
from PyQt6.QtCore import Qt

from ui.components.sidebar import ArgosSidebar, SidebarMenuItem, PageID


class TestSidebarMenuItem:
    """Test cases for SidebarMenuItem class."""
    
    @pytest.fixture
    def menu_item(self, qtbot):
        """Create a SidebarMenuItem instance for testing."""
        item = SidebarMenuItem(PageID.DASHBOARD, "📊", "대시보드")
        qtbot.addWidget(item)
        return item
    
    def test_menu_item_created(self, menu_item):
        """Test that menu item is created without error."""
        assert menu_item is not None
        assert menu_item.page_id == PageID.DASHBOARD
        assert menu_item.height() == 44
        
    def test_menu_item_inactive_by_default(self, menu_item):
        """Test that menu item is inactive by default."""
        assert menu_item.is_active() is False
        
    def test_menu_item_set_active(self, menu_item, qtbot):
        """Test setting menu item active state."""
        menu_item.set_active(True)
        assert menu_item.is_active() is True
        
        menu_item.set_active(False)
        assert menu_item.is_active() is False
    
    def test_menu_item_click_emits_signal(self, menu_item, qtbot):
        """Test that clicking menu item emits clicked signal."""
        with qtbot.waitSignal(menu_item.clicked, timeout=1000) as blocker:
            # Simulate mouse click
            qtbot.mouseClick(menu_item, Qt.MouseButton.LeftButton)
            
        # Verify signal was emitted with correct page ID
        assert blocker.signal_triggered
        emitted_args = blocker.args
        assert len(emitted_args) == 1
        assert emitted_args[0] == PageID.DASHBOARD


class TestArgosSidebar:
    """Test cases for ArgosSidebar class."""
    
    @pytest.fixture
    def sidebar(self, qtbot):
        """Create an ArgosSidebar instance for testing."""
        sidebar = ArgosSidebar()
        qtbot.addWidget(sidebar)
        return sidebar
    
    def test_sidebar_created(self, sidebar):
        """Test that sidebar is created without error."""
        assert sidebar is not None
        assert sidebar.objectName() == "sidebar"
        
    def test_sidebar_fixed_width_expanded(self, sidebar):
        """Test that sidebar width is 220px in expanded state."""
        assert sidebar.width() == 220
        assert sidebar.maximumWidth() == 220
        
    def test_sidebar_has_six_menu_items(self, sidebar):
        """Test that sidebar contains 6 SidebarMenuItem instances."""
        menu_items = sidebar.findChildren(SidebarMenuItem)
        assert len(menu_items) == 6
        
        # Verify all expected page IDs are present
        page_ids = {item.page_id for item in menu_items}
        expected_page_ids = {
            PageID.DASHBOARD, PageID.UPLOAD, PageID.ROI,
            PageID.ANALYSIS, PageID.RESULTS, PageID.SETTINGS
        }
        assert page_ids == expected_page_ids
        
    def test_navigate_to_emits_signal(self, sidebar, qtbot):
        """Test that navigate_to emits page_changed signal."""
        with qtbot.waitSignal(sidebar.page_changed, timeout=1000) as blocker:
            sidebar.navigate_to(PageID.UPLOAD)
            
        # Verify signal was emitted with correct page ID
        assert blocker.signal_triggered
        emitted_args = blocker.args
        assert len(emitted_args) == 1
        assert emitted_args[0] == PageID.UPLOAD
        
    def test_navigate_to_sets_active_item(self, sidebar):
        """Test that navigate_to sets the correct menu item as active."""
        # Navigate to ROI page
        sidebar.navigate_to(PageID.ROI)
        
        # Check that ROI item is active and others are not
        for page_id, menu_item in sidebar._menu_items.items():
            if page_id == PageID.ROI:
                assert menu_item.is_active() is True
            else:
                assert menu_item.is_active() is False
                
    def test_collapse_toggle_changes_width(self, sidebar, qtbot):
        """Test that collapse button changes sidebar width."""
        # Initially expanded
        assert sidebar.width() == 220
        assert sidebar._is_collapsed is False
        
        # Click collapse button
        qtbot.mouseClick(sidebar._collapse_button, Qt.MouseButton.LeftButton)
        
        # Wait for animation to complete (animation takes 200ms)
        qtbot.wait(300)
        
        # Should be collapsed
        assert sidebar._is_collapsed is True
        assert sidebar.maximumWidth() == 56
        
    def test_expand_toggle_changes_width(self, sidebar, qtbot):
        """Test that expand button changes sidebar width back."""
        # First collapse
        sidebar._collapse()
        qtbot.wait(300)
        assert sidebar._is_collapsed is True
        
        # Click expand button
        qtbot.mouseClick(sidebar._collapse_button, Qt.MouseButton.LeftButton)
        qtbot.wait(300)
        
        # Should be expanded
        assert sidebar._is_collapsed is False
        assert sidebar.maximumWidth() == 220
        
    def test_set_step_progress_updates_label(self, sidebar):
        """Test that set_step_progress updates the progress label."""
        sidebar.set_step_progress(9, 50)
        assert sidebar._progress_label.text() == "Step 9 / 50"
        
        sidebar.set_step_progress(15, 50)
        assert sidebar._progress_label.text() == "Step 15 / 50"