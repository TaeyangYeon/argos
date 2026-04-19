"""
Tests for Step 49 — Dashboard & Workflow final integration.

Covers:
- WorkflowIndicator 5-step rendering
- Step state transitions (pending → active → done)
- Dashboard StatCard for 검사 목적
- Signal wiring from MainWindow to DashboardPage
- Full workflow sequence state tracking
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from core.image_store import ImageStore, ImageType
from core.models import InspectionPurpose, ROIConfig


# Ensure QApplication exists for widget tests
@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# WorkflowIndicator tests
# ---------------------------------------------------------------------------

class TestWorkflowIndicator:
    """Tests for WorkflowIndicator 5-step update."""

    def test_renders_five_steps(self):
        """WorkflowIndicator should have exactly 5 steps."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        assert len(indicator._steps) == 5

    def test_step_labels_korean(self):
        """All 5 step labels must match the expected Korean text."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        expected_labels = [
            "이미지 업로드",
            "ROI 설정",
            "검사 목적 입력",
            "분석 실행",
            "결과 확인",
        ]
        actual_labels = [s._label for s in indicator._steps]
        assert actual_labels == expected_labels

    def test_all_steps_pending_initially(self):
        """All steps should start in 'pending' state."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        for step in indicator._steps:
            assert step.get_state() == "pending"

    def test_step_transition_pending_to_done(self):
        """A step can transition from pending to done."""
        from ui.components.workflow_indicator import WorkflowStep

        step = WorkflowStep(1, "Test")
        assert step.get_state() == "pending"
        step.set_state("done")
        assert step.get_state() == "done"

    def test_step_transition_to_active(self):
        """A step can transition to active state."""
        from ui.components.workflow_indicator import WorkflowStep

        step = WorkflowStep(1, "Test")
        step.set_state("active")
        assert step.get_state() == "active"

    def test_invalid_state_raises(self):
        """Setting an invalid state should raise ValueError."""
        from ui.components.workflow_indicator import WorkflowStep

        step = WorkflowStep(1, "Test")
        with pytest.raises(ValueError):
            step.set_state("invalid_state")

    def test_update_from_store_images_only(self):
        """With images but no ROI/purpose/results, only step 1 is done."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        store = ImageStore()
        store.add = MagicMock()
        store.count = MagicMock(return_value=3)

        indicator.update_from_store(store, has_roi=False, has_results=False, has_purpose=False)

        assert indicator._steps[0].get_state() == "done"     # images
        assert indicator._steps[1].get_state() == "pending"   # ROI
        assert indicator._steps[2].get_state() == "pending"   # purpose
        assert indicator._steps[3].get_state() == "pending"   # analysis
        assert indicator._steps[4].get_state() == "pending"   # results

    def test_update_from_store_all_prereqs_done(self):
        """With images + ROI + purpose but no results, step 4 should be active."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        store = ImageStore()
        store.count = MagicMock(return_value=5)

        indicator.update_from_store(store, has_roi=True, has_results=False, has_purpose=True)

        assert indicator._steps[0].get_state() == "done"     # images
        assert indicator._steps[1].get_state() == "done"     # ROI
        assert indicator._steps[2].get_state() == "done"     # purpose
        assert indicator._steps[3].get_state() == "active"   # analysis ready
        assert indicator._steps[4].get_state() == "pending"  # results

    def test_update_from_store_all_done(self):
        """With everything complete, steps 1-4 done and step 5 active."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        store = ImageStore()
        store.count = MagicMock(return_value=5)

        indicator.update_from_store(store, has_roi=True, has_results=True, has_purpose=True)

        assert indicator._steps[0].get_state() == "done"    # images
        assert indicator._steps[1].get_state() == "done"    # ROI
        assert indicator._steps[2].get_state() == "done"    # purpose
        assert indicator._steps[3].get_state() == "done"    # analysis
        assert indicator._steps[4].get_state() == "active"  # results viewable

    def test_reset_all_pending(self):
        """reset() should set all steps back to pending."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        store = ImageStore()
        store.count = MagicMock(return_value=5)
        indicator.update_from_store(store, has_roi=True, has_results=True, has_purpose=True)

        indicator.reset()
        for step in indicator._steps:
            assert step.get_state() == "pending"

    def test_backward_compatibility_no_purpose_arg(self):
        """update_from_store without has_purpose kwarg defaults to False."""
        from ui.components.workflow_indicator import WorkflowIndicator

        indicator = WorkflowIndicator()
        store = ImageStore()
        store.count = MagicMock(return_value=5)

        # Call without has_purpose — should default to False
        indicator.update_from_store(store, has_roi=True, has_results=False)
        assert indicator._steps[2].get_state() == "pending"  # purpose not set


# ---------------------------------------------------------------------------
# Dashboard StatCard tests
# ---------------------------------------------------------------------------

class TestDashboardPurposeCard:
    """Tests for the 검사 목적 StatCard on DashboardPage."""

    def _make_dashboard(self):
        from ui.pages.dashboard_page import DashboardPage

        store = ImageStore()
        km = MagicMock()
        km.list_saved_providers.return_value = []
        return DashboardPage(store, km)

    def test_purpose_card_exists(self):
        """Dashboard should have a 검사 목적 StatCard."""
        dash = self._make_dashboard()
        assert dash._purpose_card is not None

    def test_purpose_card_default_value(self):
        """Purpose card should show '미입력' by default."""
        dash = self._make_dashboard()
        assert dash._purpose_card._value == "미입력"

    def test_purpose_card_default_color_gray(self):
        """Purpose card should use gray accent color by default."""
        dash = self._make_dashboard()
        assert dash._purpose_card._accent_color == "#9E9E9E"

    def test_purpose_card_updates_on_confirmed(self):
        """After on_purpose_confirmed, card should show '확정됨' with green accent."""
        dash = self._make_dashboard()
        purpose = InspectionPurpose(inspection_type="치수측정")
        dash.on_purpose_confirmed(purpose)

        assert dash._purpose_card._value == "확정됨"
        assert dash._purpose_card._accent_color == "#43A047"

    def test_purpose_card_shows_type_in_subtitle(self):
        """After confirmation, the inspection type should appear as subtitle."""
        dash = self._make_dashboard()
        purpose = InspectionPurpose(inspection_type="결함검출")
        dash.on_purpose_confirmed(purpose)

        assert dash._purpose_card._subtitle == "결함검출"

    def test_roi_confirmed_sets_flag(self):
        """on_roi_confirmed should set _has_roi flag."""
        dash = self._make_dashboard()
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        dash.on_roi_confirmed(roi)
        assert dash._has_roi is True

    def test_analysis_complete_sets_flag(self):
        """on_analysis_complete should set _has_results flag."""
        dash = self._make_dashboard()
        dash.on_analysis_complete({"feature": None})
        assert dash._has_results is True

    def test_refresh_updates_image_counts(self):
        """refresh() should update image count stat cards from ImageStore."""
        from ui.pages.dashboard_page import DashboardPage

        store = ImageStore()
        km = MagicMock()
        km.list_saved_providers.return_value = []
        dash = DashboardPage(store, km)

        # Add mock image data to store
        with patch.object(store, "count") as mock_count:
            mock_count.side_effect = lambda t=None: {
                None: 10,
                ImageType.ALIGN_OK: 3,
                ImageType.INSPECTION_OK: 4,
                ImageType.INSPECTION_NG: 3,
            }.get(t, 0)

            dash.refresh()

            assert dash._align_ok_card._value == "3"
            assert dash._inspection_ok_card._value == "4"
            assert dash._inspection_ng_card._value == "3"
            assert dash._total_card._value == "10"


# ---------------------------------------------------------------------------
# Full workflow sequence test
# ---------------------------------------------------------------------------

class TestFullWorkflowSequence:
    """Test the complete workflow sequence end-to-end."""

    def _make_dashboard(self):
        from ui.pages.dashboard_page import DashboardPage

        store = ImageStore()
        km = MagicMock()
        km.list_saved_providers.return_value = []
        return DashboardPage(store, km)

    def test_full_sequence_state_transitions(self):
        """Simulate upload → ROI → purpose → analysis → result transitions."""
        from ui.pages.dashboard_page import DashboardPage

        store = ImageStore()
        km = MagicMock()
        km.list_saved_providers.return_value = []
        dash = DashboardPage(store, km)

        wi = dash._workflow_indicator

        # Initial state — all pending
        with patch.object(store, "count", return_value=0):
            dash.refresh()
        for step in wi._steps:
            assert step.get_state() == "pending"

        # Step 1: Images uploaded
        with patch.object(store, "count", return_value=5):
            dash.refresh()
        assert wi._steps[0].get_state() == "done"
        assert wi._steps[1].get_state() == "pending"

        # Step 2: ROI confirmed
        roi = ROIConfig(x=10, y=10, width=200, height=200)
        dash.on_roi_confirmed(roi)
        with patch.object(store, "count", return_value=5):
            dash.refresh()
        assert wi._steps[1].get_state() == "done"

        # Step 3: Purpose confirmed
        purpose = InspectionPurpose(inspection_type="결함검출")
        dash.on_purpose_confirmed(purpose)
        with patch.object(store, "count", return_value=5):
            dash.refresh()
        assert wi._steps[2].get_state() == "done"
        assert wi._steps[3].get_state() == "active"  # analysis ready

        # Step 4-5: Analysis complete
        dash.on_analysis_complete({"feature": None})
        with patch.object(store, "count", return_value=5):
            dash.refresh()
        assert wi._steps[3].get_state() == "done"
        assert wi._steps[4].get_state() == "active"  # results viewable


# ---------------------------------------------------------------------------
# MainWindow signal wiring tests
# ---------------------------------------------------------------------------

class TestMainWindowSignalWiring:
    """Test that MainWindow correctly wires signals to DashboardPage."""

    @patch("ui.main_window.DARK_THEME_QSS", "")
    def test_purpose_signal_reaches_dashboard(self):
        """purpose_confirmed on PurposePage should reach DashboardPage."""
        from ui.main_window import MainWindow

        with patch.object(MainWindow, "_setup_toolbar"):
            with patch.object(MainWindow, "_setup_status_bar"):
                win = MainWindow()

        dash = win._pages[PageID.DASHBOARD]
        purpose = InspectionPurpose(inspection_type="형상검사", description="test shape inspection for quality")
        win._pages[PageID.PURPOSE].purpose_confirmed.emit(purpose)

        assert dash._has_purpose is True
        assert dash._purpose_type == "형상검사"

    @patch("ui.main_window.DARK_THEME_QSS", "")
    def test_analysis_complete_signal_reaches_dashboard(self):
        """analysis_complete on AnalysisPage should reach DashboardPage."""
        from ui.main_window import MainWindow

        with patch.object(MainWindow, "_setup_toolbar"):
            with patch.object(MainWindow, "_setup_status_bar"):
                win = MainWindow()

        dash = win._pages[PageID.DASHBOARD]
        aggregate = {"feature": None, "align": None}
        win._pages[PageID.ANALYSIS].analysis_complete.emit(aggregate)

        assert dash._has_results is True

    @patch("ui.main_window.DARK_THEME_QSS", "")
    def test_roi_signal_reaches_dashboard(self):
        """roi_confirmed on ROIPage should reach DashboardPage."""
        from ui.main_window import MainWindow

        with patch.object(MainWindow, "_setup_toolbar"):
            with patch.object(MainWindow, "_setup_status_bar"):
                win = MainWindow()

        dash = win._pages[PageID.DASHBOARD]
        roi = ROIConfig(x=0, y=0, width=100, height=100)
        win._pages[PageID.ROI].roi_confirmed.emit(roi)

        assert dash._has_roi is True

    @patch("ui.main_window.DARK_THEME_QSS", "")
    def test_purpose_data_flows_to_analysis_page(self):
        """InspectionPurpose should flow from PurposePage to AnalysisPage."""
        from ui.main_window import MainWindow

        with patch.object(MainWindow, "_setup_toolbar"):
            with patch.object(MainWindow, "_setup_status_bar"):
                win = MainWindow()

        purpose = InspectionPurpose(
            inspection_type="치수측정",
            description="measure hole diameter accurately",
        )
        win._pages[PageID.PURPOSE].purpose_confirmed.emit(purpose)

        # MainWindow stores it and passes to AnalysisPage
        assert win._inspection_purpose is not None
        assert win._inspection_purpose.inspection_type == "치수측정"


# Import PageID at module level for MainWindow tests
from ui.components.sidebar import PageID
