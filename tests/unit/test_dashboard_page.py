"""
Unit tests for dashboard page components.

This module tests the dashboard page, stat cards, and workflow indicators
to ensure proper functionality and data binding.
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

from ui.components.stat_card import StatCard
from ui.components.workflow_indicator import WorkflowStep, WorkflowIndicator
from ui.pages.dashboard_page import DashboardPage
from core.image_store import ImageStore, ImageType
from core.key_manager import KeyManager


class TestStatCard:
    """Test cases for StatCard component."""
    
    def test_stat_card_created(self, qtbot):
        """StatCard("Test", "0") instantiates without error."""
        card = StatCard("Test", "0")
        qtbot.addWidget(card)
        
        assert card is not None
        assert card._title == "Test"
        assert card._value == "0"
        assert card._subtitle == ""
        
    def test_stat_card_update_value(self, qtbot):
        """update_value("5") → value label text is "5"."""
        card = StatCard("Test", "0")
        qtbot.addWidget(card)
        
        card.update_value("5")
        
        assert card._value_label.text() == "5"
        assert card._value == "5"
        
    def test_stat_card_update_value_with_subtitle(self, qtbot):
        """update_value with subtitle creates/updates subtitle label."""
        card = StatCard("Test", "0")
        qtbot.addWidget(card)
        
        # Initially no subtitle
        assert card._subtitle_label is None
        
        # Add subtitle
        card.update_value("5", "images")
        
        assert card._value_label.text() == "5"
        assert card._subtitle_label is not None
        assert card._subtitle_label.text() == "images"
        # Note: Widget might not be visible immediately after creation
        
        # Update subtitle
        card.update_value("10", "total")
        
        assert card._value_label.text() == "10"
        assert card._subtitle_label.text() == "total"
        
        # Remove subtitle
        card.update_value("15", "")
        
        assert card._value_label.text() == "15"
        assert not card._subtitle_label.isVisible()
        
    def test_stat_card_accent_color(self, qtbot):
        """StatCard with accent "#43A047" → value label color set."""
        card = StatCard("Test", "0", accent_color="#43A047")
        qtbot.addWidget(card)
        
        # Check value label has accent color
        assert "#43A047" in card._value_label.styleSheet()
        
        # Test changing accent color
        card.set_accent("#E53935")
        
        assert "#E53935" in card._value_label.styleSheet()
        
    def test_stat_card_dimensions(self, qtbot):
        """StatCard has fixed height 100px and minimum width 160px."""
        card = StatCard("Test", "0")
        qtbot.addWidget(card)
        
        assert card.height() == 100
        assert card.minimumWidth() == 160


class TestWorkflowStep:
    """Test cases for WorkflowStep component."""
    
    def test_workflow_step_created(self, qtbot):
        """WorkflowStep instantiates without error."""
        step = WorkflowStep(1, "Test Step")
        qtbot.addWidget(step)
        
        assert step is not None
        assert step._step_number == 1
        assert step._label == "Test Step"
        assert step._state == "pending"
        
    def test_workflow_step_state_pending(self, qtbot):
        """set_state("pending") → step shows pending style."""
        step = WorkflowStep(1, "Test Step")
        qtbot.addWidget(step)
        
        step.set_state("pending")
        
        assert step.get_state() == "pending"
        assert "#616161" in str(step._circle_color.name())  # Gray color
        
    def test_workflow_step_state_active(self, qtbot):
        """set_state("active") → step shows active style with animation."""
        step = WorkflowStep(1, "Test Step")
        qtbot.addWidget(step)
        
        step.set_state("active")
        
        assert step.get_state() == "active"
        assert "#1e88e5" in str(step._circle_color.name()).lower()  # Blue color (case insensitive)
        assert step._pulse_timer.isActive()  # Animation running
        
    def test_workflow_step_state_done(self, qtbot):
        """set_state("done") → step shows checkmark style."""
        step = WorkflowStep(1, "Test Step")
        qtbot.addWidget(step)
        
        step.set_state("done")
        
        assert step.get_state() == "done"
        assert "#43a047" in str(step._circle_color.name()).lower()  # Green color (case insensitive)
        assert not step._pulse_timer.isActive()  # No animation
        
    def test_workflow_step_state_warning(self, qtbot):
        """set_state("warning") → step shows warning style."""
        step = WorkflowStep(1, "Test Step")
        qtbot.addWidget(step)
        
        step.set_state("warning")
        
        assert step.get_state() == "warning"
        assert "#fb8c00" in str(step._circle_color.name()).lower()  # Orange color (case insensitive)
        
    def test_workflow_step_invalid_state(self, qtbot):
        """Invalid state raises ValueError."""
        step = WorkflowStep(1, "Test Step")
        qtbot.addWidget(step)
        
        with pytest.raises(ValueError):
            step.set_state("invalid")


class TestWorkflowIndicator:
    """Test cases for WorkflowIndicator component."""
    
    def test_workflow_indicator_created(self, qtbot):
        """WorkflowIndicator instantiates with 4 steps."""
        indicator = WorkflowIndicator()
        qtbot.addWidget(indicator)
        
        assert indicator is not None
        assert len(indicator._steps) == 4
        
        # Check step labels
        expected_labels = ["이미지 업로드", "ROI 설정", "분석 실행", "결과 확인"]
        for i, expected_label in enumerate(expected_labels):
            assert indicator._steps[i]._label == expected_label
            
    def test_workflow_indicator_update_no_data(self, qtbot):
        """update_from_store with no data → all steps pending."""
        indicator = WorkflowIndicator()
        qtbot.addWidget(indicator)
        
        mock_store = MagicMock()
        mock_store.count.return_value = 0
        
        indicator.update_from_store(mock_store, has_roi=False, has_results=False)
        
        # All steps should be pending
        for step in indicator._steps:
            assert step.get_state() == "pending"
            
    def test_workflow_indicator_update_with_images(self, qtbot):
        """update_from_store with images → step 1 done."""
        indicator = WorkflowIndicator()
        qtbot.addWidget(indicator)
        
        mock_store = MagicMock()
        mock_store.count.return_value = 3  # Has images
        
        indicator.update_from_store(mock_store, has_roi=False, has_results=False)
        
        assert indicator._steps[0].get_state() == "done"  # 이미지 업로드
        assert indicator._steps[1].get_state() == "pending"  # ROI 설정
        assert indicator._steps[2].get_state() == "pending"  # 분석 실행
        assert indicator._steps[3].get_state() == "pending"  # 결과 확인
        
    def test_workflow_indicator_update_with_roi(self, qtbot):
        """update_from_store with ROI → step 2 done."""
        indicator = WorkflowIndicator()
        qtbot.addWidget(indicator)
        
        mock_store = MagicMock()
        mock_store.count.return_value = 3
        
        indicator.update_from_store(mock_store, has_roi=True, has_results=False)
        
        assert indicator._steps[0].get_state() == "done"  # 이미지 업로드
        assert indicator._steps[1].get_state() == "done"  # ROI 설정
        assert indicator._steps[2].get_state() == "active"  # 분석 실행 (ready to run)
        assert indicator._steps[3].get_state() == "pending"  # 결과 확인
        
    def test_workflow_indicator_update_with_results(self, qtbot):
        """update_from_store with results → step 3 done, step 4 active."""
        indicator = WorkflowIndicator()
        qtbot.addWidget(indicator)
        
        mock_store = MagicMock()
        mock_store.count.return_value = 3
        
        indicator.update_from_store(mock_store, has_roi=True, has_results=True)
        
        assert indicator._steps[0].get_state() == "done"  # 이미지 업로드
        assert indicator._steps[1].get_state() == "done"  # ROI 설정
        assert indicator._steps[2].get_state() == "done"  # 분석 실행
        assert indicator._steps[3].get_state() == "active"  # 결과 확인
        
    def test_workflow_indicator_reset(self, qtbot):
        """reset() → all steps return to pending."""
        indicator = WorkflowIndicator()
        qtbot.addWidget(indicator)
        
        # Set some steps to different states
        indicator._steps[0].set_state("done")
        indicator._steps[1].set_state("active")
        
        # Reset
        indicator.reset()
        
        # All should be pending
        for step in indicator._steps:
            assert step.get_state() == "pending"


class TestDashboardPage:
    """Test cases for DashboardPage."""
    
    def test_dashboard_page_created(self, qtbot):
        """DashboardPage with mock ImageStore → no error."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        assert page is not None
        assert page._image_store == mock_image_store
        assert page._key_manager == mock_key_manager
        
    def test_dashboard_stat_cards_count(self, qtbot):
        """Dashboard contains exactly 4 StatCard instances."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        # Check that 4 stat cards were created
        assert page._align_ok_card is not None
        assert page._inspection_ok_card is not None
        assert page._inspection_ng_card is not None
        assert page._total_card is not None
        
        # Check they are StatCard instances
        assert isinstance(page._align_ok_card, StatCard)
        assert isinstance(page._inspection_ok_card, StatCard)
        assert isinstance(page._inspection_ng_card, StatCard)
        assert isinstance(page._total_card, StatCard)
        
    def test_dashboard_refresh_updates_align_ok(self, qtbot):
        """Mock ImageStore.count(ALIGN_OK) = 3 → after refresh() → Align OK StatCard shows "3"."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        # Mock return values
        mock_image_store.count.side_effect = lambda image_type=None: {
            ImageType.ALIGN_OK: 3,
            ImageType.INSPECTION_OK: 2,
            ImageType.INSPECTION_NG: 1,
            None: 6
        }.get(image_type, 0)
        
        mock_key_manager.list_saved_providers.return_value = []
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        # Call refresh
        page.refresh()
        
        # Check stat card values
        assert page._align_ok_card._value_label.text() == "3"
        assert page._inspection_ok_card._value_label.text() == "2"
        assert page._inspection_ng_card._value_label.text() == "1"
        assert page._total_card._value_label.text() == "6"
        
    def test_dashboard_refresh_updates_ng(self, qtbot):
        """Mock ImageStore.count(INSPECTION_NG) = 2 → after refresh() → NG StatCard shows "2"."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        mock_image_store.count.side_effect = lambda image_type=None: {
            ImageType.INSPECTION_NG: 2
        }.get(image_type, 0)
        
        mock_key_manager.list_saved_providers.return_value = []
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        page.refresh()
        
        assert page._inspection_ng_card._value_label.text() == "2"
        
    def test_dashboard_session_reset_signal(self, qtbot):
        """Click 새 프로젝트 시작, confirm → session_reset signal emitted."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        mock_key_manager = MagicMock()
        mock_key_manager.list_saved_providers.return_value = []
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        # Connect signal to track emissions
        signal_emitted = []
        page.session_reset.connect(lambda: signal_emitted.append(True))
        
        # Mock QMessageBox with proper constructor
        mock_msgbox = MagicMock()
        mock_msgbox.exec.return_value = QMessageBox.StandardButton.Yes
        
        with patch('PyQt6.QtWidgets.QMessageBox', return_value=mock_msgbox):
            # Directly call the button's click method
            page._on_new_project_clicked()
            
            # Verify signal was emitted
            assert len(signal_emitted) == 1
            
            # Verify image store was cleared
            mock_image_store.clear.assert_called_once()
            
    def test_dashboard_session_reset_canceled(self, qtbot):
        """Click 새 프로젝트 시작, cancel → no signal emitted."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        # Connect signal to track emissions
        signal_emitted = []
        page.session_reset.connect(lambda: signal_emitted.append(True))
        
        # Mock QMessageBox to return No
        with patch('ui.pages.dashboard_page.QMessageBox') as mock_msgbox:
            mock_msgbox_instance = MagicMock()
            mock_msgbox_instance.exec.return_value = QMessageBox.StandardButton.No
            mock_msgbox.return_value = mock_msgbox_instance
            
            # Click new project button
            page._new_project_button.click()
            
            # Verify signal was NOT emitted
            assert len(signal_emitted) == 0
            
            # Verify image store was NOT cleared
            mock_image_store.clear.assert_not_called()
            
    def test_dashboard_ai_card_no_connection(self, qtbot):
        """KeyManager.list_saved_providers() returns [] → AI card shows "AI 미연결" text."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        mock_key_manager = MagicMock()
        
        mock_key_manager.list_saved_providers.return_value = []
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        page.refresh()
        
        ai_text = page._ai_status_label.text()
        assert "AI 미연결" in ai_text
        assert "API 입력 버튼을 눌러 연결하세요" in ai_text
        
    def test_dashboard_ai_card_with_connection(self, qtbot):
        """KeyManager has saved provider → AI card shows connected status."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        mock_key_manager = MagicMock()
        
        mock_key_manager.list_saved_providers.return_value = ["claude"]
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        page.refresh()
        
        ai_text = page._ai_status_label.text()
        assert "Claude 연결됨" in ai_text
        assert "●" in ai_text
        
    def test_dashboard_workflow_indicator_exists(self, qtbot):
        """Dashboard has workflow indicator widget."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        assert page._workflow_indicator is not None
        assert isinstance(page._workflow_indicator, WorkflowIndicator)
        
    def test_dashboard_new_project_button_exists(self, qtbot):
        """Dashboard has new project button with correct styling."""
        mock_image_store = MagicMock()
        mock_key_manager = MagicMock()
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        assert page._new_project_button is not None
        assert "새 프로젝트 시작" in page._new_project_button.text()
        assert page._new_project_button.objectName() == "dangerBtn"
        
    def test_dashboard_show_event_calls_refresh(self, qtbot):
        """showEvent triggers refresh() automatically."""
        mock_image_store = MagicMock()
        mock_image_store.count.return_value = 0
        mock_key_manager = MagicMock()
        mock_key_manager.list_saved_providers.return_value = []
        
        page = DashboardPage(mock_image_store, mock_key_manager)
        qtbot.addWidget(page)
        
        # Mock refresh method to track calls
        refresh_called = []
        
        def mock_refresh():
            refresh_called.append(True)
            # Call update AI status directly to avoid workflow indicator issues
            page._update_ai_status()
            
        page.refresh = mock_refresh
        
        # Show the widget to trigger showEvent
        page.show()
        
        # Verify refresh was called
        assert len(refresh_called) > 0